# import hvac
# import logging
# from hvac.exceptions import InvalidPath
# from model import ResultModel

# logger = logging.getLogger("VaultUtil")
# logging.basicConfig()
# logger.setLevel(logging.INFO)

# class VaultUtil():
#     def __init__(self,address:str,token:str,unseal_key:str) -> None:
#         self.__client=hvac.Client(url=address,token=token)
#         if self.__client.sys.is_sealed() == True:
#             self.__client.sys.submit_unseal_key(unseal_key)

#     def get_secret(self,engine_name:str,path:str):
#         try:
#             response=self.__client.secrets.kv.v2.read_secret_version(mount_point=engine_name,path=path)
#             value = response['data']['data']
#             return value
#         except Exception as e:
#             if isinstance(e,InvalidPath):
#                 logger.error("InvalifPath")
#                 return ResultModel(0,"Secret path is invalid")
#             else:
#                 raise e
        

# vault=VaultUtil('http://localhost:8200',
#           'hvs.sV8GgIzHlxpznnHhbbFhPttX',
#           'cb90c15e7246fe9a535223b13fe50a1dcaa08833f5970763dae3e4bc96268003')

# value=vault.get_secret('kvv','test','key')
