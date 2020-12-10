from ansible.module_utils.basic import AnsibleModule
from ansible_collections.onepassword.connect.plugins.module_utils import specs, api, errors, fields
from ansible.module_utils.common.text.converters import to_native

DOCUMENTATION = '''
module: item_info
author:
  - 1Password (@1Password)
requirements:
notes:
short_description: Returns information about a 1Password Item
description:
  - The name or ID of an item can be given.
  - It is possible to return information about a specific field instead of an item.
  - If no vaults are specified, the module searches every vault accessible by the API token.
options:
  item:
    type: str
    required: True
    description:
      - Name or ID of the item as shown in the 1Password UI.
  field: str
    type: str
    description:
      - Name of specific field for the Item
  vault: str
    type: str
    description:
      - Name or ID of the Vault in which the Item is stored.
      - If not specified, the module searches through every vault accessible by the API token. 
extends_documentation_fragment:
  - onepassword.connect.api_params
'''

EXAMPLES = '''
- name: Find and return Item details for "Dev-Database" in vault with ID "2zbeu4smcibizsuxmyvhdh57b6"
  onepassword.connect.item_info:
    item: Dev-Database 
    vault= 2zbeu4smcibizsuxmyvhdh57b6

- name: Find and return Item details for Item with ID "lixyh6993asdfq9njdzf221d3z" in vault with ID "2zbeu4smcibizsuxmyvhdh57b6"
  onepassword.connect.item_info:
    item: lixyh6993asdfq9njdzf221d3z 
    vault: 2zbeu4smcibizsuxmyvhdh57b6

- name: Find and return Item details for Item with ID "lixyh6993asdfq9njdzf221d3z" without specifying the vault
  onepassword.connect.item_info:
    item: lixyh6993asdfq9njdzf221d3z 
    
- name: Return 'key' field for Item "Dev-Database" in vault with ID "2zbeu4smcibizsuxmyvhdh57b6"
  onepassword.connect.item_info:
    item: Dev-Database 
    field: key 
    vault: 2zbeu4smcibizsuxmyvhdh57b6

- name: Return 'secretKey' field for Item with ID 'lixyh6993asdfq9njdzf221d3z' in vault with ID "2zbeu4smcibizsuxmyvhdh57b6"
  onepassword.connect.item_info:
    item: lixyh6993asdfq9njdzf221d3z
    field: secretKey 
    vault: 2zbeu4smcibizsuxmyvhdh57b6

- name: Return 'ccNumber' field for Item 'Business Visa' in Vault 'Office Expenses'
  onepassword.connect.item_info:
    item: Business Visa
    field: ccNumber 
    vault: Office Expenses
'''

RETURN = '''
op_item:
  description: Dictionary containing Item properties. See 1Password API specs for complete structure.
  type: complex
  returned: when field option is not set
field:
  description: Value of the field for the Item.
  type: string
  returned: when field option is set
'''


def _get_item(op, item, vault_id):
    try:
        return op.get_item_by_id(vault_id, item)
    except (errors.NotFoundError, errors.BadRequestError):
        response = op.get_item_by_name(vault_id, item)
        return op.get_item_by_id(vault_id, response["id"])


def _get_item_field(item, selected_field):
    for field in item["fields"]:
        if field["label"] == selected_field:
            return field["value"]
    raise errors.NotFoundError


def _get_item_with_vault_id(op, item, vault_id):
    return _get_item(op, item, vault_id)


def _get_item_without_vault(op, item):
    vaults = op.get_vaults()
    for vault in vaults:
        try:
            return _get_item_with_vault_id(op, item, vault["id"])
        except errors.NotFoundError:
            pass
    raise errors.NotFoundError


def _try_get_item(op, item, vault):
    api_response = {}
    if vault:
        try:
            api_response = _get_item_with_vault_id(op, item, vault)
        except errors.BadRequestError:
            vault = op.get_vault_id_by_name(vault)
            api_response = _get_item_with_vault_id(op, item, vault)
    else:
        api_response = _get_item_without_vault(op, item)
    return api_response


def main():
    arg_spec = specs.op_item_info()

    module = AnsibleModule(
        argument_spec=arg_spec,
        supports_check_mode=True,
    )

    api_client = api.create_client(module)
    field = module.params.get("field")
    vault = module.params.get("vault")
    item = module.params.get("item")

    result = {"op_item": {}}
    api_response = {}

    try:
        api_response = _try_get_item(api_client, item, vault)
        if field:
            field_value = _get_item_field(api_response, field)
            result.update({"field": field_value})
        else:
            api_response["fields"] = fields.flatten_fieldset(api_response["fields"])
            result.update({"op_item": api_response})
    except errors.NotFoundError:
        result.update({"msg": "Item not found"})
    except TypeError as e:
        result.update({"msg": to_native("Invalid Item config: {err}").format(err=e)})
    except errors.Error as e:
        result.update({"msg": to_native(e.message)})
    module.exit_json(**result)


if __name__ == '__main__':
    main()