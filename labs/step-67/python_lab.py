from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from sqlalchemy import ForeignKey,CheckConstraint,select,text
from sqlalchemy.orm import DeclarativeBase,Mapped,mapped_column,relationship,selectinload
from labs.shared.orm_lab import check,run
from labs.shared.workflow_lab import seed
from labs.shared.extensions_lab import extra_tables

class Mapping(DeclarativeBase):pass
class Node(Mapping):
    __tablename__='hierarchy_nodes'
    __table_args__=(CheckConstraint('parent_id IS NULL OR parent_id<>id'),)
    id:Mapped[int]=mapped_column(primary_key=True)
    name:Mapped[str]
    parent_id:Mapped[int|None]=mapped_column(ForeignKey('hierarchy_nodes.id'))
    parent:Mapped['Node|None']=relationship(remote_side=[id],back_populates='children')
    children:Mapped[list['Node']]=relationship(back_populates='parent')

def descendants(identity):
    tree=select(Node.id).where(Node.id==identity).cte('descendants',recursive=True)
    return tree.union_all(select(Node.id).join(tree,Node.parent_id==tree.c.id))

def reparent(session,schema,identity,parent):
    # All application reparent operations use this lock and READ COMMITTED.
    session.execute(text('SELECT pg_advisory_xact_lock(hashtext(current_database()),hashtext(:s))'),{'s':schema})
    node=session.get(Node,identity,populate_existing=True)
    if node is None or (parent is not None and session.get(Node,parent) is None):raise LookupError('Unknown node')
    tree=descendants(identity)
    if parent is not None and session.scalar(select(tree.c.id).where(tree.c.id==parent)) is not None:raise ValueError('Hierarchy cycle')
    node.parent_id=parent;session.flush()

def scenario(lab):
    seed(lab)
    with extra_tables(lab,Mapping.metadata):
        with lab.session() as s,s.begin():
            root=Node(id=1,name='Lab');computer=Node(id=2,name='Computer',parent=root)
            s.add_all([root,computer,Node(id=3,name='Component',parent=computer),Node(id=4,name='Other room')])
        with lab.session() as s:
            check(set(s.scalars(select(descendants(1).c.id)))=={1,2,3},'Recursive CTE traverses a lab, computer and contained component.')
            root=s.scalar(select(Node).where(Node.id==1).options(selectinload(Node.children)))
            check(root.children[0].parent.id==1,'remote_side and back_populates distinguish self-referencing scalar and collection paths.')
        try:
            with lab.session() as s,s.begin():reparent(s,lab.schema,1,3)
        except ValueError:check(True,'The serialized reparent service rejects moving an ancestor under its own descendant.')
        else:raise AssertionError('Cycle accepted')
        with lab.session() as s,s.begin():reparent(s,lab.schema,2,4)
        with lab.session() as s:check(set(s.scalars(select(descendants(4).c.id)))=={2,3,4},'Valid reparenting preserves the entire descendant subtree.')
        first=lab.driver();second=lab.driver();first.execute('BEGIN')
        try:
            first.execute('SELECT pg_advisory_xact_lock(hashtext(current_database()),hashtext(%s))',(lab.schema,))
            second.execute("SET lock_timeout='150ms'")
            import psycopg
            try:second.execute('SELECT pg_advisory_xact_lock(hashtext(current_database()),hashtext(%s))',(lab.schema,))
            except psycopg.errors.LockNotAvailable:check(True,'Independent backends demonstrate that competing controlled hierarchy mutations serialize.')
            else:raise AssertionError('Hierarchy lock bypass')
        finally:first.execute('ROLLBACK')
        check(lab.driver().execute(f'SELECT parent_id FROM {lab.schema}.hierarchy_nodes WHERE id=2').fetchone()[0]==4,'Independent SQL observes the permitted hierarchy move.')
    print('Policy: cross-row cycle protection applies to the controlled reparent service under READ COMMITTED; arbitrary direct SQL writers must not bypass it. The self-FK alone cannot enforce acyclicity.')

if __name__=='__main__':run(67,scenario)
