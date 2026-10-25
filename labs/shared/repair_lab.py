"""Prepare a repair through the same service commands used by HTTP routes."""
from college_maintenance.workflow import report_ticket, transition_ticket
from college_maintenance.repairs import create_order,start_order,set_part_line,edit_order
from college_maintenance.attachments import attachment_metadata

def prepare(lab,ids,store,parts=(),labor='5.00'):
    with lab.session() as session,session.begin():
        ticket=report_ticket(session,ids['reporter'],asset_id=ids['asset'],title='Repair fixture',description='Synthetic end-to-end issue')
        transition_ticket(session,ids['admin'],ticket.id,action='assign',technician_id=ids['tech'])
        order=create_order(session,ids['tech'],ticket.id)
        for part_id,amount in parts:set_part_line(session,ids['tech'],order.id,part_id,amount)
        edit_order(session,ids['tech'],order.id,labor_cost=labor,completion_note='Repair completed with synthetic proof')
        data=b'synthetic completion proof';key=store.put(data)
        attachment_metadata(session,store,ids['tech'],order.id,kind='work_order',storage_key=key,data=data,filename='proof.bin',content_type='application/octet-stream')
        start_order(session,ids['tech'],order.id)
        return ticket.id,order.id
