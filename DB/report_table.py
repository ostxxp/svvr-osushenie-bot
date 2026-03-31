from DB.docs_fetching import client
from DB import database_funcs, objects_fetching
import re
from bot.bot_init import bot

def extract_sheet_key(link):
    match = re.search(r'/d/([a-zA-Z0-9-_]+)', link)
    if match:
        return match.group(1)
    else:
        bot.send_message(chat_id=403953652, text=f"Неправильная ссылка на таблицу: {link}")


async def create_table_report(id):
    object = await objects_fetching.fetch_objects_by_name(await database_funcs.get_obj_name(id))
    link = object[3]

    with open(f'report_info/{id}.txt', 'r', encoding='utf-8') as file:
        lines = file.readlines()
    key = extract_sheet_key(link)
    try:
        spreadsheet = client.open_by_key(key)
        worksheet = spreadsheet.sheet1
        all_values = worksheet.get_all_values()

        row = await database_funcs.get_column(id)
        worksheet.update_cell(int(row), 2, lines[0])
        if len(lines) > 1:
            for k in range(1, len(lines) - 1):
                worksheet.update_cell(int(row), all_values[0].index(lines[k].split()[0]) + 1, float(lines[k].split()[1].strip()))
            worksheet.update_cell(int(row), 3, "\n".join(sorted(lines[-1].split(','))))
    except:
        bot.send_message(chat_id=403953652, text=f"Неправильная ссылка на таблицу: {link}")


async def find_date(id, link, date):
    try:
        key = extract_sheet_key(link)
        spreadsheet = client.open_by_key(key)
        worksheet = spreadsheet.sheet1
        values = worksheet.col_values(2)
        for dates in values:
            if date == dates.strip():
                return "exists"
        await database_funcs.set_column(id, str(len(values) + 1))
        return None
    except:
        bot.send_message(chat_id=403953652, text=f"Неправильная ссылка на таблицу: {link}")
