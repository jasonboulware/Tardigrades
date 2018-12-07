
_thirdpartyaccount_type_list = []
def register_thirdpartyaccount_type(thirdpartyaccount_type):
    _thirdpartyaccount_type_list.append(thirdpartyaccount_type)

def get_thirdpartyaccount_types():
    return _thirdpartyaccount_type_list

register_thirdpartyaccount_type(('thirdpartyaccounts', 'TwitterAccount'))
register_thirdpartyaccount_type(('thirdpartyaccounts', 'FacebookAccount'))
