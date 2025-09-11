from DB.docs_fetching import client

spreadsheet = client.open_by_key('1OtnMFqU6-m-JsWyFX2GLG6HksRd18K0su4-INlcjN8A')
worksheet = spreadsheet.get_worksheet(2)


async def add_feedback(id):
    with open(f'feedbacks_temp/{id}.txt', 'r', encoding='utf-8') as file:
        lines = file.readlines()[0].split('|', 3)

    date = lines[0]
    time = lines[1]
    username = lines[2]
    text = lines[3]

    num = len(worksheet.get_all_values()) + 1

    worksheet.update([[date]], f"A{num}")
    worksheet.update([[time]], f"B{num}")
    worksheet.update([[username]], f"C{num}")
    worksheet.update([[text]], f"D{num}")
