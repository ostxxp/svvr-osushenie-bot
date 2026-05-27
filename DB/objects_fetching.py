from DB.docs_fetching import client
from DB.prorabs_fetching import get_prorabs

spreadsheet = client.open_by_key('1OtnMFqU6-m-JsWyFX2GLG6HksRd18K0su4-INlcjN8A')
worksheet = spreadsheet.get_worksheet(1)

async def fetch_objects(id):
    all_values = worksheet.get_all_values()
    data = all_values[4:]

    for prorab in await get_prorabs():
        if prorab[0] != '' and int(prorab[0]) == id:
            name = prorab[1]
            break
    else:
        return None
    objects = []
    for d in data:
        try:
            if name in d[2]:
                objects.append(d)
        except:
            pass
    return objects

async def fetch_objects_names(id):
    objects = await fetch_objects(id)
    if objects is None:
        return None
    return [obj[1] for obj in objects]

async def fetch_objects_by_id(id, obj_id):
    objects = await fetch_objects(id)
    if objects is None:
        return None

    for obj in objects:
        if str(obj[0]) == str(obj_id):
            return obj
    return None

async def fetch_objects_by_name(name):
    all_values = worksheet.get_all_values()
    data = all_values[4:]
    for d in data:
        if d[1] == name:
            return d


def add_link(location, link):
    worksheet.update(location, [[link]])

