from pprint import pprint

from portalsdk import APIContext, APIMethodType, APIRequest

api_context = APIContext()
api_context.api_key = 'yi8gkb9h69w28nn12ej2nef5ftpj0zuv'
api_context.public_key = 'MIICIjANBgkqhkiG9w0BAQEFAAOCAg8AMIICCgKCAgEAmptSWqV7cGUUJJhUBxsMLonux24u+FoTlrb+4Kgc6092JIszmI1QUoMohaDDXSVueXx6IXwYGsjjWY32HGXj1iQhkALXfObJ4DqXn5h6E8y5/xQYNAyd5bpN5Z8r892B6toGzZQVB7qtebH4apDjmvTi5FGZVjVYxalyyQkj4uQbbRQjgCkubSi45Xl4CGtLqZztsKssWz3mcKncgTnq3DHGYYEYiKq0xIj100LGbnvNz20Sgqmw/cH+Bua4GJsWYLEqf/h/yiMgiBbxFxsnwZl0im5vXDlwKPw+QnO2fscDhxZFAwV06bgG0oEoWm9FnjMsfvwm0rUNYFlZ+TOtCEhmhtFp+Tsx9jPCuOd5h2emGdSKD8A6jtwhNa7oQ8RtLEEqwAn44orENa1ibOkxMiiiFpmmJkwgZPOG/zMCjXIrrhDWTDUOZaPx/lEQoInJoE2i43VN/HTGCCw8dKQAwg0jsEXau5ixD0GUothqvuX3B9taoeoFAIvUPEq35YulprMM7ThdKodSHvhnwKG82dCsodRwY428kg2xM/UjiTENog4B6zzZfPhMxFlOSFX4MnrqkAS+8Jamhy1GgoHkEMrsT5+/ofjCx0HjKbT5NuA2V/lmzgJLl3jIERadLzuTYnKGWxVJcGLkWXlEPYLbiaKzbJb2sYxt+Kt5OxQqC1MCAwEAAQ=='
api_context.ssl = True
api_context.method_type = APIMethodType.POST
api_context.address = 'api.sandbox.vm.co.mz'
api_context.port = 18352
api_context.path = '/ipg/v1x/c2bPayment/singleStage/'
    
api_context.add_header('Origin', '*')

async def mpesa_gest_charging(input_trans_id: str, mpesa_contact: str, amount: str, ThirdPartyRef: str = 'BUYAMZ', ServiceProviderCode: str = '171717'):

    api_context.add_parameter('input_TransactionReference',input_trans_id)
    api_context.add_parameter('input_CustomerMSISDN',mpesa_contact)
    api_context.add_parameter('input_Amount',amount)
    api_context.add_parameter('input_ThirdPartyReference',ThirdPartyRef)
    api_context.add_parameter('input_ServiceProviderCode',ServiceProviderCode)


    api_request = APIRequest(api_context)
    result = api_request.execute()
    return result