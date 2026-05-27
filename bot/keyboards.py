from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from DB import objects_fetching, groups_fetching, database_funcs
from DB import installers_fetching

yes_no_keyboard = InlineKeyboardMarkup(
    inline_keyboard=[[InlineKeyboardButton(text="✅ Да", callback_data="yes"),
                      InlineKeyboardButton(text="❌ Нет", callback_data="submit_no")]]
)

yes_no_feedback_keyboard = InlineKeyboardMarkup(
    inline_keyboard=[[InlineKeyboardButton(text="✅ Отправить", callback_data="feedback_yes"),
                      InlineKeyboardButton(text="❌ Отмена", callback_data="abort")]]
)

feedback_button = [InlineKeyboardButton(text="Предложить улучшение 👍🏻", callback_data=f"feedback")]
feedback_keyboard = InlineKeyboardMarkup(inline_keyboard=[feedback_button])

async def objects_to_keyboard(id):
    buttons = []
    objects = await objects_fetching.fetch_objects(id)
    if objects is not None:
        for obj in objects:
            buttons.append([InlineKeyboardButton(text=obj[1], callback_data=f"obj_{id}_{obj[0]}")])
        buttons.append(feedback_button)
        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
        return keyboard
    return None

async def objects_to_keyboard_by_names(id, obj_names):
    buttons = []
    objects = await objects_fetching.fetch_objects(id) or []
    for obj_name in obj_names:
        for obj in objects:
            if obj[1] == obj_name:
                buttons.append([InlineKeyboardButton(text=obj_name, callback_data=f"obj_{id}_{obj[0]}")])
                break
    buttons.append(feedback_button)
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    return keyboard

async def groups_to_keyboard(id, is_general, iteration, group_number = None):
    buttons = []
    groups = groups_fetching.groups
    for group in groups:
        if group[0].count('.') == iteration:
            if group_number is None or group[0].startswith(f"{group_number}."):
                if len(group[1]) > 85:
                    name = f"{group[1][:85]}..."
                else:
                    name = group[1]
                buttons.append([InlineKeyboardButton(text=f"{group[0]}. {name}", callback_data=group[0])])

    if is_general:
        buttons.append([InlineKeyboardButton(text="👨🏻‍🔧 Выбрать рабочих", callback_data="installers")])
    elif group_number.count('.') > 0:
        num = '.'.join(group_number.split('.')[:-1])
        buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data=num)])
    else:
        buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data=f"back_to_day_{await database_funcs.get_report_date(id)}")])
    buttons.append([InlineKeyboardButton(text="🙅🏻‍♂️ Отменить заполнение", callback_data="abort")])
    groups = InlineKeyboardMarkup(inline_keyboard=buttons)
    return groups

async def installers_to_keyboard(id, filter=None):
    buttons = []
    if filter is None:
        k = 0
        for installer in await installers_fetching.fetch_installers():
            if k < 3:
                inst = str(installer[1])
                if (await database_funcs.get_installers(id) is not None) and installer[1] in (await database_funcs.get_installers(id)):
                    inst = "✅ " + inst
                buttons.append([InlineKeyboardButton(text=inst, callback_data=f"installer_{installer[1]}")])
                k += 1
            else:
                inst = str(installer[1])
                if (await database_funcs.get_installers(id) is not None) and installer[1] in (await database_funcs.get_installers(id)):
                    inst = "✅ " + inst
                    buttons.append([InlineKeyboardButton(text=inst, callback_data=f"installer_{installer[1]}")])

        buttons.append(
            [InlineKeyboardButton(text="...", callback_data=f"none")]
        )
    else:
        for installer in await installers_fetching.fetch_installers():
            inst = str(installer[1])
            if inst.lower().startswith(filter):
                if (await database_funcs.get_installers(id) is not None) and installer[1] in (await database_funcs.get_installers(id)):
                    inst = "✅ " + inst
                buttons.append([InlineKeyboardButton(text=inst, callback_data=f"installer_{installer[1]}")])
    buttons.append(
        [InlineKeyboardButton(text="🔙 Назад", callback_data=f"back_to_day_{await database_funcs.get_report_date(id)}")])
    buttons.append([InlineKeyboardButton(text="Отправить📨", callback_data=f"submit_{await database_funcs.get_report_date(id)}")])
    buttons.append([InlineKeyboardButton(text="🙅🏻‍♂️ Отменить заполнение", callback_data="abort")])
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    return keyboard
