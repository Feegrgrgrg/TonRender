import asyncio
from aiocryptopay import AioCryptoPay, Networks



async def create_invoice(amount):
    try:
        crypto = AioCryptoPay(token='13459:AAWdM9gvN5GXqXwu2ebpNRP6FodaMIPcHBu', network=Networks.TEST_NET) #Test_NET заменить на MAIN_NET
        invoice = await crypto.create_invoice(asset='USDT', amount=amount)
        invoice_id = invoice.invoice_id
        return invoice.bot_invoice_url, invoice_id
    except Exception as e:
        print("Ошибка при создании чека:", e)
        return None, None


async def check_invoice_payment(invoice_id):
    try:
        crypto = AioCryptoPay(token='13459:AAWdM9gvN5GXqXwu2ebpNRP6FodaMIPcHBu', network=Networks.TEST_NET)#Test_NET заменить на MAIN_NET
        while True:
            invoice_details = await crypto.get_invoices(invoice_ids=[invoice_id])
            if isinstance(invoice_details, list):
                if invoice_details[0].status == 'paid':
                    return True
                else:
                    await asyncio.sleep(10)
            else:
                print("Неверный формат данных при получении информации о чеке.")
                return False
    except Exception as e:
        print("Ошибка при проверке оплаты чека:", e)
        return False
    
    
async def send_invoice_to_user(user_id):

    payment_url, invoice_id = await create_invoice()

    if payment_url:
        print(f"Ссылка на оплату чека: {payment_url}")
        if invoice_id:
            payment_status = await check_invoice_payment(invoice_id)
            if payment_status:
                print('оплачен')
            else:
                print('не оплачен')
        else:
            print('не удалось получить Id')
    else:
        print('чек не создан')
   
async def main2():
    payment_url, invoice_id = await create_invoice(0.1)