from seleniumwire import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from oauth2client.service_account import ServiceAccountCredentials
from bert4keras.snippets import longest_common_subsequence
from PIL import Image, ImageChops
import apiclient.discovery
import requests
import os
import httplib2
import json
import time
import shutil


"""
    Функция чтения json-файла

    :param     filename: Название файла
    :type      filename: str.
    
    :returns: dict или list
"""


def json_load(filename):
    with open(filename, "r", encoding="utf8") as read_file:
        result = json.load(read_file)
    return result


"""
    Функция записи в json-файл

    :param     filename: Название файла
    :type      filename: str.
    :param     data: Записываемые данные
    :type      data: list or dict.
  
"""


def json_dump(filename, data):
    with open(filename, "w", encoding="utf8") as write_file:
        json.dump(data, write_file, ensure_ascii=False)


"""
    Функция отправки сообщения в телеграм 
    
    :param tg_token: Токен телеграм-бота из BotFather
    :type  tg_token: str.
    :param  chat_id: Список ID пользователей бота
    :type   chat_id: list.
    :param     text: Отправляемый текст сообщения
    :type      text: str.
    :param     text: Список дескрипторов отправляемых фото
    :type      text: list.    

"""


def send_msg(tg_token, chat_id, text, photo=False):

    if photo != False:
        files = photo[1]

    for id_user in chat_id:

        if photo == False:
            url_req = (
                "https://api.telegram.org/bot"
                + tg_token
                + "/sendMessage"
                + "?parse_mode=HTML&chat_id="
                + str(id_user)
                + "&text="
                + text
            )
            results = requests.get(url_req)

        else:
            url_req = "https://api.telegram.org/bot" + tg_token + "/sendMediaGroup"
            params = {"chat_id": str(id_user), "media": json.dumps(photo[0])}

            result = requests.post(url_req, params=params, files=files)

    if photo != False:
        for key in files.keys():
            files[key].close()



"""
    Функция получения списка ссылок для обращения к api wildberries для указанных в гугл-таблице артикулов
    
    :param driver: Вебдрайвер
    :type  driver: WebDriver .
    :param  artikuls: Список артикулов их гугл-табблицы
    :type   artikuls: list.
    :param     text: Отправляемый текст сообщения
    :type      text: str.
    :param  chat_id: Список ID пользователей бота
    :type   chat_id: list. 
    :param tg_token: Токен телеграм-бота из BotFather
    :type  tg_token: str.
    
    
    :returns: list
"""
def get_urls(driver, artikuls, chat_id, tg_token):

    new_artikul_flag = False
    json_urls_dict = json_load(r"./json/urls.json")

    result = []
    for artikul in artikuls:
        if artikul not in json_urls_dict.keys():
            new_artikul_flag = True
            driver.get(
                "https://www.wildberries.ru/catalog/{}/detail.aspx".format(artikul)
            )
            element = WebDriverWait(driver, 20).until(
                EC.presence_of_element_located((By.ID, "productNmId"))
            )

            for request in driver.requests:
                if request.response:
                    if (
                        request.url.endswith("card.json")
                        and str(artikul) in request.url
                    ):
                        json_urls_dict[artikul] = request.url
                        result.append(request.url)
                        break
        else:

            result.append(json_urls_dict[artikul])

    if new_artikul_flag:
        send_msg(tg_token,chat_id, "Список артикулов обновлен")

    json_dump(r"./json/urls.json", json_urls_dict)

    return list(set(result))

"""
    Функция загрузки фото из карточки товара
    

    :param  artikul: Артикул товара
    :type   artikul: int.
    :param  imgs_count: Число картинок
    :type   imgs_count: int. 

"""
def download_imgs(artikul, imgs_count):
    files = os.listdir(r"./photos/{}".format(artikul))
    files_count = len(files)
    for num in range(1, imgs_count + 1):
        save_path = ""

        if len(files) == 1:
            save_path = r"./photos/{}/{}.jpg".format(artikul, num)
        else:
            save_path = r"./photos/{}/compare/{}.jpg".format(artikul, num)

        p = requests.get(img_url.format(num))
        if p.status_code != 404 and p.status_code != 200:
            print(p.status_code)
        if p.status_code == 200:
            out = open(save_path, "wb")
            out.write(p.content)
            out.close()


"""
    Функция сравнения двух картинок
    

    :param  pic1: Путь до первой картинки
    :type   pic1: str.
    :param  pic2: Путь до второй картинки
    :type   pic2: str. 

"""
def check_pictures(pic1, pic2):
    pic_1 = Image.open(pic1)
    pic_2 = Image.open(pic2)

    pic_1.thumbnail((400, 300))
    pic_2.thumbnail((400, 300))

    res = ImageChops.difference(pic_1, pic_2).getbbox()
    pic_1.close()
    pic_2.close()
    if res is None:
        return True
    else:
        return False



"""
    Функция поиска одинаковых картинок после повторного парсинга
    
    :param  artikul: Артикул товара
    :type   artikul: str.

    :returns: list
"""

def compare_imgs(artikul):
    similar_imgs = []
    for file_name in os.listdir(r"./photos/{}".format(artikul)):
        if ".jpg" in file_name:

            img1_path = r"./photos/{}/".format(artikul) + file_name

            for file_compare in os.listdir(r"./photos/{}/compare/".format(artikul)):

                img2_path = r"./photos/{}/compare/".format(artikul) + file_compare

                if img2_path in similar_imgs:
                    continue

                if check_pictures(img1_path, img2_path):

                    similar_imgs.append(img1_path)
                    similar_imgs.append(img2_path)
                    break
    return similar_imgs




"""
    Функция сравнения двух словарей с целью поиска измененных, удаленных и добавленных свойств в карточку товара 
    
    :param  new_dict: Исходный словарь 
    :type   new_dict: dicr.
    :param  old_dict: Сравниваемый словарь 
    :type   old_dict: dicr.
    
    :returns: str
"""

def compare_dicts(new_dict, old_dict):
    compate_res = {}
    compate_res["add"] = []
    compate_res["remove"] = []
    compate_res["changed"] = []
    msg_srting = ""
    for option_name in new_dict.keys():

        if option_name in old_dict.keys():

            if str(new_dict[option_name]).lower() != str(old_dict[option_name]).lower():

                compate_res["changed"].append(
                    "<em>"
                    + str(option_name)
                    + ":</em>\n\t\t<b>Было:</b> "
                    + str(old_dict[option_name])
                    + "\n\t\t<b>Стало:</b> "
                    + str(new_dict[option_name])
                    + "\n\n"
                )
        else:
            compate_res["add"].append(
                "<em>"
                + str(option_name)
                + ":</em> "
                + str(new_dict[option_name])
                + "\n\n"
            )

    for option_name in old_dict.keys():
        if option_name not in new_dict.keys():
            compate_res["remove"].append(
                "<em>"
                + str(option_name)
                + ":</em> "
                + str(old_dict[option_name])
                + "\n\n"
            )

    if len(compate_res["changed"]) != 0:
        msg_srting += "<b><em>Изменено:</em></b>\n"

        for added in compate_res["changed"]:
            msg_srting += added

    if len(compate_res["add"]) != 0:
        msg_srting += "<b><em>Добавлено:</em></b>\n"

        for added in compate_res["add"]:
            msg_srting += added

    if len(compate_res["remove"]) != 0:
        msg_srting += "<b><em>Удалено:</em></b>\n"

        for added in compate_res["remove"]:
            msg_srting += added

    return msg_srting


"""
    Функция поиска различий в двух текстах 
    
    :param  source: Исходная строка
    :type   source: str.
    :param  target: Сравниваемая строка
    :type   target: str.
    
    :returns: list
"""

def compare(source, target):
    _, mapping = longest_common_subsequence(source, target)
    source_idxs = set([i for i, j in mapping])
    target_idxs = set([j for i, j in mapping])
    colored_source, colored_target = "", ""
    result = []

    for i, j in enumerate(target):
        if i in target_idxs or j == " ":
            colored_target += j
        else:

            colored_target += "<b>{}</b>".format(j)

    for i, j in enumerate(source):
        if i in source_idxs or j == " ":
            colored_source += j
        else:
            colored_source += "<b>{}</b>".format(j)

    for text in [colored_source, colored_target]:

        colored_text = text.replace("\n", " *transfer* ")
        res_text = ""
        split_text = colored_text.split(sep=None)
        for word in split_text:
            if "<b>" in word:
                new_word = word.replace("<b>", "").replace("</b>", "")

                split_text[split_text.index(word)] = "<b><u>{}</u></b>".format(new_word)

        result.append(" ".join(split_text).replace("*transfer* ", "\n"))

    return result


n        = json_load(r"./json/n.json")[0] + 1
config   = json_load(r"./json/config.json")

tg_token              = config['tg_token']
SAMPLE_SPREADSHEET_ID = config['SAMPLE_SPREADSHEET_ID']
CREDENTIALS_FILE      = r"./json/creds.json"

creds = ServiceAccountCredentials.from_json_keyfile_name(
    CREDENTIALS_FILE, ["https://www.googleapis.com/auth/spreadsheets"]
)
httpAuth   = creds.authorize(httplib2.Http())
service    = apiclient.discovery.build("sheets", "v4", http=httpAuth)
iter_count = 0
chrome_options = Options()
chrome_options.add_argument("--headless")
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")
driver = webdriver.Chrome(chrome_options=chrome_options)


while True:
    now = time.time()
    try:
        artikuls_info = {}
        user_ids_list = []
        
        # шаблоны сообщений
        text_name        = 'На <a href="https://www.wildberries.ru/catalog/{}/detail.aspx">{}</a> изменились название.\n{}'
        text_img         = 'На <a href="https://www.wildberries.ru/catalog/{}/detail.aspx">{}</a> изменились фото.\n'
        text_description = 'На <a href="https://www.wildberries.ru/catalog/{}/detail.aspx">{}</a> изменилось описание.\n{}'
        text_composition = 'На <a href="https://www.wildberries.ru/catalog/{}/detail.aspx">{}</a> изменился состав.\n{}'
        text_options     = 'На <a href="https://www.wildberries.ru/catalog/{}/detail.aspx">{}</a> изменились характеристики.\n{}'
        text_grounded    = 'На <a href="https://www.wildberries.ru/catalog/{}/detail.aspx">{}</a> изменились расширенные характеристики.\n{}'

        resp = (
            service.spreadsheets()
            .values()
            .batchGet(
                spreadsheetId=SAMPLE_SPREADSHEET_ID, ranges=["Лист1!A2:B", "Лист1!D2:D"]
            )
            .execute()
        )
        
        artikuls_info_list = resp["valueRanges"][0]["values"]
        for artikul_data in artikuls_info_list:
            artikuls_info[artikul_data[0]] = artikul_data[1]


        user_ids = resp["valueRanges"][1]["values"]
        for user_id in user_ids:
            user_ids_list.append(user_id[0])

        json_urls = get_urls(driver, artikuls_info.keys(), user_ids_list, tg_token)

        for url in json_urls:

            card_info = requests.get(url).json()

            imgs_count = card_info["media"]["photo_count"]
            artikul = url.replace("/info/ru/card.json", "").split("/")[-1]
            img_url = url.replace("info/ru/card.json", "images/big/{}.webp")
            del_imgs = []
            add_imgs = []
            new_artikul_flag = False
            
            # добавление сведений о новом артикуле
            if not os.path.exists(r"./photos/{}".format(artikul)):
                os.mkdir(r"./photos/{}".format(artikul))
                os.mkdir(r"./photos/{}/compare".format(artikul))
                card_info_json = {}
                new_artikul_flag = True
                card_info_json["imt_name"] = (
                    card_info["imt_name"] if "imt_name" in card_info.keys() else ""
                )
                card_info_json["description"] = (
                    card_info["description"]
                    if "description" in card_info.keys()
                    else ""
                )
                card_info_json["grouped_options"] = (
                    card_info["grouped_options"]
                    if "grouped_options" in card_info.keys()
                    else ""
                )
                card_info_json["options"] = (
                    card_info["options"] if "options" in card_info.keys() else ""
                )
                card_info_json["compositions"] = (
                    card_info["compositions"]
                    if "compositions" in card_info.keys()
                    else ""
                )

                json_dump(r"./json/{}.json".format(artikul), card_info_json)
                download_imgs(artikul, imgs_count)
            
            # блок поиск внесенных изменений в карточку товара
            if not new_artikul_flag:
                download_imgs(artikul, imgs_count)

                card_info_json = json_load(r"./json/{}.json".format(artikul))

                # Название
                if "imt_name" in card_info.keys():
                    if card_info_json["imt_name"] != "":

                        if card_info_json["imt_name"] != card_info["imt_name"]:

                            text_with_tags = compare(
                                card_info_json["imt_name"], card_info["imt_name"]
                            )

                            msg_text = (
                                "\n<b>Было название</b>: \n"
                                + text_with_tags[0]
                                + "\n\n\n<b>Стало</b>: \n"
                                + text_with_tags[1]
                            )
                            send_msg(tg_token,
                                user_ids_list,
                                text_name.format(
                                    artikul, artikuls_info[artikul], msg_text
                                ),
                            )
                    else:
                        msg_text = (
                            "\n<b>Добавлено название</b>:  <em>"
                            + card_info["imt_name"]
                            + "</em>"
                        )
                        send_msg(tg_token,
                            user_ids_list,
                            text_name.format(artikul, artikuls_info[artikul], msg_text),
                        )

                else:
                    if card_info_json["imt_name"] != "":
                        msg_text = "название удалено из карточки"
                        send_msg(tg_token,
                            user_ids_list,
                            text_name.format(artikul, artikuls_info[artikul], msg_text),
                        )

                # Описание
                if "description" in card_info.keys():
                    if card_info_json["description"] != "":

                        if card_info_json["description"] != card_info["description"]:

                            text_with_tags = compare(
                                card_info_json["description"], card_info["description"]
                            )

                            msg_text = (
                                "\n<b>Было описание</b>: \n"
                                + text_with_tags[0]
                                + "\n\n\n<b>Стало</b>: \n"
                                + text_with_tags[1]
                            )
                            send_msg(tg_token,
                                user_ids_list,
                                text_description.format(
                                    artikul, artikuls_info[artikul], msg_text
                                ),
                            )
                    else:
                        msg_text = (
                            "\n<b>Добавлено описание</b>:  <em>"
                            + card_info["description"]
                            + "</em>"
                        )
                        send_msg(tg_token,
                            user_ids_list,
                            text_description.format(
                                artikul, artikuls_info[artikul], msg_text
                            ),
                        )

                else:
                    if card_info_json["description"] != "":
                        msg_text = "Описание удалено из карточки"
                        send_msg(tg_token,
                            user_ids_list,
                            text_description.format(
                                artikul, artikuls_info[artikul], msg_text
                            ),
                        )

                # Состав
                if "compositions" in card_info.keys():
                    if card_info_json["compositions"] != "":
                        compositions_1 = []
                        compositions_2 = []
                        for composition in card_info_json["compositions"]:
                            compositions_1.append(composition["name"])

                        for composition in card_info["compositions"]:
                            compositions_2.append(composition["name"])

                        if ", ".join(compositions_1) != ", ".join(compositions_2):

                            msg_text = (
                                "\n<b>Был состав</b>:  <em>"
                                + ", ".join(compositions_1)
                                + "</em>\n<b>Стал</b>:  <em>"
                                + ", ".join(compositions_2)
                                + "</em>"
                            )
                            send_msg(tg_token,
                                user_ids_list,
                                text_composition.format(
                                    artikul, artikuls_info[artikul], msg_text
                                ),
                            )

                    else:
                        new_composition_string = ""
                        for composition in card_info["compositions"]:
                            new_composition_string += composition["name"]
                        msg_text = (
                            "<b>Добавили состав:</b> <em>"
                            + new_composition_string
                            + "</em>"
                        )
                        send_msg(tg_token,
                            user_ids_list,
                            text_composition.format(
                                artikul, artikuls_info[artikul], msg_text
                            ),
                        )

                else:
                    if card_info_json["compositions"] != "":
                        msg_text = "<b>Состав удален из карточки</b> "
                        send_msg(tg_token,
                            user_ids_list,
                            text_composition.format(
                                artikul, artikuls_info[artikul], msg_text
                            ),
                        )

                # Опции

                options_dict_1 = {}
                options_dict_2 = {}
                if "options" in card_info.keys():
                    if card_info_json["options"] != "":

                        for options in card_info_json["options"]:
                            options_dict_1[options["name"]] = options["value"]

                        for options in card_info["options"]:
                            options_dict_2[options["name"]] = options["value"]

                        msg_text = compare_dicts(options_dict_2, options_dict_1)

                        if msg_text != "":
                            send_msg(tg_token,
                                user_ids_list,
                                text_options.format(
                                    artikul, artikuls_info[artikul], msg_text
                                ),
                            )

                    else:
                        new_options_string = []
                        for options in card_info["options"]:
                            new_options_string.append(
                                ":".join([options["name"], options["value"]]) + "\n"
                            )

                        msg_text = (
                            "<b>Добавили характеристики:</b>\n<em>"
                            + "".join(new_options_string)
                            + "</em>"
                        )
                        send_msg(tg_token,
                            user_ids_list,
                            text_options.format(
                                artikul, artikuls_info[artikul], msg_text
                            ),
                        )

                else:
                    if card_info_json["options"] != "":
                        msg_text = "<b>Характеристики удалены из карточки</b> "
                        send_msg(tg_token,
                            user_ids_list,
                            text_options.format(
                                artikul, artikuls_info[artikul], msg_text
                            ),
                        )

                # Расширенные опции
                if "grouped_options" in card_info.keys():
                    if card_info_json["grouped_options"] != "":
                        options_1 = {}
                        options_2 = {}
                        for options in card_info_json["grouped_options"]:
                            for option in options["options"]:
                                if option["name"] not in options_dict_1.keys():
                                    options_1[option["name"]] = option["value"]

                        for options in card_info["grouped_options"]:
                            for option in options["options"]:
                                if option["name"] not in options_dict_2.keys():
                                    options_2[option["name"]] = option["value"]

                        msg_text = compare_dicts(options_2, options_1)

                        if msg_text != "":
                            send_msg(tg_token,
                                user_ids_list,
                                text_grounded.format(
                                    artikul, artikuls_info[artikul], msg_text
                                ),
                            )

                    else:
                        new_options_string = []
                        for options in card_info["grouped_options"]:
                            for option in options["options"]:
                                if option["name"] not in options_dict_1.keys():
                                    new_options_string.append(
                                        ":".join([option["name"], option["value"]])
                                    )

                        msg_text = (
                            "<b>Добавили расширенные характеристики:</b>\n<em>"
                            + "".join(new_options_string)
                            + "</em>"
                        )
                        send_msg(tg_token,
                            user_ids_list,
                            text_grounded.format(
                                artikul, artikuls_info[artikul], msg_text
                            ),
                        )

                else:
                    if card_info_json["grouped_options"] != "":
                        msg_text = (
                            "<b>Расширенные характеристики удалены из карточки</b> "
                        )
                        send_msg(tg_token,
                            user_ids_list,
                            text_grounded.format(
                                artikul, artikuls_info[artikul], msg_text
                            ),
                        )
                
                # внесение изменений в json файл со сведениями об артикуле
                card_info_json["imt_name"] = (
                    card_info["imt_name"] if "imt_name" in card_info.keys() else ""
                )
                card_info_json["description"] = (
                    card_info["description"]
                    if "description" in card_info.keys()
                    else ""
                )
                card_info_json["grouped_options"] = (
                    card_info["grouped_options"]
                    if "grouped_options" in card_info.keys()
                    else ""
                )
                card_info_json["options"] = (
                    card_info["options"] if "options" in card_info.keys() else ""
                )
                card_info_json["compositions"] = (
                    card_info["compositions"]
                    if "compositions" in card_info.keys()
                    else ""
                )
                json_dump(r"./json/{}.json".format(artikul), card_info_json)
                
                
                # Поиск изменений в картинках артикула (новое фото, удаленное фото)
                photo_files = os.listdir(r"./photos/{}".format(artikul))
                compare_files = os.listdir(r"./photos/{}/compare/".format(artikul))

                while True:
                    try:
                        same_imgs = compare_imgs(artikul)
                        photo_files = os.listdir(r"./photos/{}".format(artikul))
                        compare_files = os.listdir(
                            r"./photos/{}/compare/".format(artikul)
                        )

                        break
                    except Exception as e:
                        for file_compare in compare_files:
                            img2_path = (
                                r"./photos/{}/compare/".format(artikul) + file_compare
                            )
                            if ".jpg" in file_compare:
                                os.remove(img2_path)
                        download_imgs(artikul, imgs_count)
                        continue
                    time.sleep(5)

                for file_name in photo_files:
                    img1_path = r"./photos/{}/".format(artikul) + file_name
                    if ".jpg" in file_name and img1_path not in same_imgs:
                        del_imgs.append(img1_path)

                for file_compare in compare_files:
                    img2_path = r"./photos/{}/compare/".format(artikul) + file_compare
                    if ".jpg" in file_compare and img2_path not in same_imgs:
                        add_imgs.append(img2_path)

               
                if len(del_imgs) != 0 or len(add_imgs) != 0:
                    if iter_count != 0:
                        send_msg(tg_token,
                            user_ids_list,
                            text_img.format(artikul, artikuls_info[artikul]),
                        )
                    if len(del_imgs) != 0:
                        files = {}
                        media = []

                        for img in del_imgs:
                            files["photo_{}".format(del_imgs.index(img))] = open(
                                img, "rb"
                            )
                            media.append(
                                {
                                    "type": "photo",
                                    "media": "attach://photo_{}".format(
                                        del_imgs.index(img)
                                    ),
                                }
                            )

                        media[0]["caption"] = "Удаленные фото"
                        if iter_count != 0:
                            send_msg(tg_token,user_ids_list, "", [media, files])

                    if len(add_imgs) != 0:
                        files = {}
                        media = []

                        for img in add_imgs:
                            files["photo_{}".format(add_imgs.index(img))] = open(
                                img, "rb"
                            )
                            media.append(
                                {
                                    "type": "photo",
                                    "media": "attach://photo_{}".format(
                                        add_imgs.index(img)
                                    ),
                                }
                            )

                        media[0]["caption"] = "Добавленные фото"
                        if iter_count != 0:
                            send_msg(tg_token,user_ids_list, "", [media, files])

                    shutil.copytree(
                        r"./photos/{}".format(artikul), r"./test/{}".format(n)
                    )

                n += 1
                json_dump(r"./json/n.json", [n])
                for file_name in photo_files:
                    img1_path = r"./photos/{}/".format(artikul) + file_name
                    if ".jpg" in file_name:
                        os.remove(img1_path)

                for file_compare in compare_files:
                    img2_path = r"./photos/{}/compare/".format(artikul) + file_compare
                    img1_path = r"./photos/{}/".format(artikul) + file_compare
                    if ".jpg" in file_compare:

                        shutil.move(img2_path, img1_path)

    except Exception as e:
        json_dump(r"./json/n.json", [n])
        continue

    iter_count += 1
    print(time.time() - now)
