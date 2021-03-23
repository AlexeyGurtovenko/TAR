from tinydb import TinyDB, Query, where
from trello import TrelloClient
from datetime import datetime, timezone, timedelta
from pytz import timezone as tz
import time
import math
from operator import itemgetter


class TarDriver:

    #Конструктор класса
    def __init__(self, 
                        trello_apiKey = '',                                 #apiKey для подключения к trello
                        trello_token = '',  #apiToken для подключения к trello
                        local_timezone = 'Asia/Tomsk'): 


        self.API_KEY = trello_apiKey
        self.TOKEN = trello_token
        self.local_timezone = tz(local_timezone)
        self.filter_dates = []
        self.database_is_updating = False


        #Подключение к Trello
        try:
            self.trello_client = TrelloClient(
                                            api_key=self.API_KEY,
                                            token=self.TOKEN,
            )
        except Exception as err:
            print(f'{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}: [ERROR] Failed to connect to Trello via API: {err}')
        else:
            print(f'{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}: [MSG] Connection to Trello established successful')
        

        #Создание файла БД и таблиц в БД
        try:
            self.db = TinyDB('tar_database.json')
            #self.db.drop_tables()      !!!!!!!!!!!!!!!!!!!!!

            self.report = self.db.table('report')
            self.worktime = self.db.table('worktime')
            self.local_boards = self.db.table('boards')
            self.local_lists = self.db.table('lists')
            self.local_cards = self.db.table('cards')
            self.local_persons = self.db.table('persons')
            self.local_cards_has_persons = self.db.table('cards_has_persons')

        except Exception as err:
            print(f'{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}: [ERROR] Failed to setup tar_database: {err}')
        else:
            print(f'{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}: [MSG] tar_database created')

        
        self.basic_template = [
                                {0:  'Перечень Задач', 'cards': ['П3 - Описание автоматизируемых функций', 
                                                                    'П5 - Описание информационного обеспечения', 
                                                                    'В1 - Описание входных сигналов и данных',
                                                                    'В2 - Описание выходных сигналов (сообщений)',
                                                                    'ПА - Описание программного обеспечения',
                                                                    'ПБ - Описание алгоритма',
                                                                    'П6 - Описание информационной базы',
                                                                    'С9 - Чертеж форм (видеокадра)',
                                                                    'И3 - Руководство оператора',
                                                                    'И3 - Руководство программиста',
                                                                    'И4 - Инструкция по ведению БД',
                                                                    'ПМИ - Программа и методика испытаний',
                                                                    'ПО ПЛК - Программа контроллера',
                                                                    'ПО Панели - Программа панели оператора',
                                                                    'ПО АРМ - Программа рабочего места оператора',
                                                                    'ПО БД - База данных',
                                                                    'Ежедневная планерка',
                                                                    'Планирование цели (спринт)',
                                                                    'Анализ завершения цели (спринта)']
                                },

                                {1:  'Комплекс Задач', 'cards': []},
                                {2:  'В Работе', 'cards': []},
                                {3:  'Согласование выполнения', 'cards': []},
                                {4:  'Завершены', 'cards': []},
                                {5:  'Отменены', 'cards': []}
        ]

        self.db.drop_table('worktime')
        self.worktime.insert({ 'work_day_starts': '09:00:00', 
                               'work_day_ends': '18:00:00', 
                               'work_day_duration': '09:00:00', 
                               'lunch_hours_starts': '13:00:00', 
                               'lunch_hours_ends': '14:00:00',
                               'lunch_duration': '01:00:00',
                               'day_work_hours': '08:00:00',
                               'work_days': '5', 
                               'week_work_hours': '1 day, 16:00:00',
                               'update_period': '00:02:00'
        })


    def add_board(self, board):
        #Добавление новой доски в БД
        try:
            self.local_boards.insert({'board_id': board.id, 'board_name': board.name, 'board_description': board.description,'board_last_modified': str(board.date_last_activity)})

            for list_ in board.list_lists():
                self.local_lists.insert( {'list_id': list_.id, 
                                          'list_name': list_.name, 
                                          'list_last_modified': str(datetime.now().strftime("%Y-%m-%d %H:%M:%S")), 
                                          'board_id': board.id, 
                                          'board_name': board.name}
                                        )

                for card in list_.list_cards():

                    self.local_cards.insert( {'card_id': card.id,  
                                              'card_name': card.name, 
                                              'list_id': list_.id, 
                                              'list_name': list_.name,
                                              'board_id': board.id, 
                                              'board_name': board.name}
                                            )

                    if len(card.member_id) > 0:
                        for person in self.team:
                            if person.id in card.member_id:
                                query_result = self.local_persons.get(where('person_id') == str(person.id))
                                self.local_cards_has_persons.insert({'card_id': card.id, 
                                                                         'card_name': card.name, 
                                                                         'person_id': person.id, 
                                                                         'person_name': query_result['person_fullname'],
                                                                         'list_id': list_.id,
                                                                         'list_name': list_.name,
                                                                         'board_id': board.id,
                                                                         'board_name': board.name}
                                                                    )

        except Exception as err:
            print(f'{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}: [ERROR] Failed to add "{board.name}": {err}')
        else:
            print(f'{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}: [MSG] "{board.name}" added successful')


    def delete_board(self, board_id, board_name = ''):
        #Удаление доски из БД
        try:
            #Удаляем записи из таблицы local_cards_has_persons
            self.local_cards_has_persons.remove(where('board_id') == str(board_id))
            #Удаляем записи из таблицы local_cards
            self.local_cards.remove(where('board_id') == str(board_id))
            #Удаляем записи из таблицы local_lists
            self.local_lists.remove(where('board_id') == str(board_id))
            #Удаляем записи из таблицы local_boards
            self.local_boards.remove(where('board_id') == str(board_id))
        except Exception as err:
            print(f'{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}: [ERROR] Failed to delete {board_id}: {err}')
        else:
            print(f'{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}: [MSG] {board_id} deleted successful')


    def update_board(self, board):
        #Обновление доски в БД
        datetime_format = "%Y-%m-%d %H:%M:%S.%f%z"

        try:
            query_result = self.local_boards.get(where('board_id') == str(board.id))

        except Exception as err:
            print(f'{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}: [MSG] Updating "{board.name}"...{err}')
            self.delete_board(board_id = board.id, board_name = board.name)
            self.add_board(board = board)
        else:
            board_date_last_activity = self.unify_time(datetime.strptime(query_result['board_last_modified'], datetime_format))
            
            if self.unify_time(board.date_last_activity) > board_date_last_activity:
                print(f'{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}: [MSG] Updating "{board.name}"...')
                self.delete_board(board_id = board.id, board_name = board.name)
                self.add_board(board = board)


    def fill_main_boards(self):
        #Заполнение таблиц local_boards, local_lists, local_cards
        print(f'{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}: [MSG] Filling "local_boards / local_lists / local_cards" tables...')
        try:
            for board in self.trello_client.list_boards():
                self.add_board(board = board)
        except Exception as err:
            print(f'{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}: [ERROR] Failed to fill "local_boards / local_lists / local_cards" tables: {err}')
        else:
            print(f'{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}: [MSG] "local_boards / local_lists / local_cards" tables filled successful')
   

    def fill_persons(self, team_board_name='КАДРЫ'):
        #Заполнение таблицы local_persons
        try:
            print(f'{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}: [MSG] Filling "local_persons" table...')
            for board in self.trello_client.list_boards():
                if board.name == team_board_name:
                    self.team = board.get_members(filters='all')
                    for list_ in board.list_lists():
                        for card in list_.list_cards():
                            if len(card.member_id) > 0:
                                for person in self.team:
                                    if person.id in card.member_id:
                                        self.local_persons.insert({'person_id': person.id, 'person_username': person.username, 'person_fullname': card.name, 'status': list_.name, 'last_modified': str(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))})                       
                    break
        except Exception as err:
            print(f'{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}: [ERROR] Failed to fill "local_persons" table: {err}')
        else:
            print(f'{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}: [MSG] "local_persons" table filled successful')


    def fill_cards_has_persons(self):
        #Заполнение таблицы cards_has_persons
        try:
            print(f'{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}: [MSG] Filling "cards_has_persons" table...')
            for board in self.trello_client.list_boards():
                for list_ in board.list_lists():
                    for card in list_.list_cards():
                        if len(card.member_id) > 0:
                            for person in self.team:
                                if person.id in card.member_id:
                                    query_result = self.local_persons.get(where('person_id') == str(person.id))
                                    self.local_cards_has_persons.insert({'card_id': card.id, 
                                                                         'card_name': card.name, 
                                                                         'person_id': person.id, 
                                                                         'person_name': query_result['person_fullname'],
                                                                         'list_id': list_.id,
                                                                         'list_name': list_.name,
                                                                         'board_id': board.id,
                                                                         'board_name': board.name}
                                                                         )
        except Exception as err:
            print(f'{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}: [ERROR] Failed to fill "cards_has_persons" table: {err}')
        else:
            print(f'{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}: [MSG] "cards_has_persons" table filled successful')

    
    def fill_database(self):
        self.fill_persons()
        self.fill_main_boards()

    
    def update_database(self, update_on_change = False):
        
        time_format = "%H:%M:%S"

        self.db.drop_table('persons')
        self.fill_persons()

        update = True

        while update:

            self.database_is_updating = True

            update_period_time = (time.strptime(self.get_update_period(), time_format))
            update_period_seconds = timedelta(hours=update_period_time.tm_hour, minutes=update_period_time.tm_min, seconds=update_period_time.tm_sec).total_seconds()

            print(f'{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}: [MSG] Checking for updates...')

            trello_boards = self.trello_client.list_boards()
            local_boards = self.local_boards.all()

            if len(trello_boards) > len(local_boards): #в trello добавили доску
                #ищем какую
                tempBoards = []

                for board in local_boards:
                    tempBoards.append(board['board_id'])   

                for board in trello_boards:
                    if board.id not in tempBoards: #новая доска обнаружена
                        self.add_board(board = board)
            
                print(f'{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}: [MSG] Checking for updates finished')

            elif len(trello_boards) < len(local_boards): #в trello удалили доску
                #ищем какую
                tempBoards = []

                for board in trello_boards:
                    tempBoards.append(board.id)   

                for board in local_boards:
                    if board['board_id'] not in tempBoards: #новая доска обнаружена
                        self.delete_board(board_id = board['board_id'], board_name = board['board_name'])
                
                print(f'{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}: [MSG] Checking for updates finished')

            else: #обновляем все доски. Новых / удаленных не обнаружено
                for board in trello_boards:
                    self.update_board(board = board)
                
                print(f'{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}: [MSG] Checking for updates finished')

                if not update_on_change:
                    time.sleep(update_period_seconds)
                    
                    self.database_is_updating = False

            



    def get_persons_active_tasks(self, person_id, active_list_name = 'В Работе'):
        query_result = self.local_cards_has_persons.search((where('person_id') == str(person_id)) & (where('list_name') == str(active_list_name)))
        return len(query_result)


    # !!!!! Изменить чтоб читал пользователей доски, возможно вернуть board_has_persons
    def get_project_members(self, board_id):
        temp_persons = []
        board_persons = []
        query_result = self.local_cards_has_persons.search(where('board_id') == str(board_id))
        for result in query_result:
            if result['person_id'] not in temp_persons:
                temp_persons.append(result['person_id'])
                board_persons.append({'person_id': result['person_id'], 'person_name': result['person_name']})
        return board_persons


    def get_tasks_on_board(self, board_id, list_name = 'В работе'):
        tasks = []
        query_result = self.local_cards.search(where('board_id') == str(board_id))
        for result in query_result:

            if result['list_name'] == list_name:

                query_result_ = self.local_cards_has_persons.search(where('list_id') == str(result['list_id']))
                for result_ in query_result_:
                    if result_['card_name'] == result['card_name']:
                        task = {'task_name': result['card_name'], 'task_member': result_['person_name'], 'card_in_work_time': result['card_in_work_time']}
                        tasks.append(task)
                        break

        return tasks


    def get_lists_by_board_id(self, board_id):
        query_result = self.local_lists.search((where('board_id') == str(board_id)))
        return query_result


    def get_active_tasks_by_person(self, person_id):
        query_result = self.local_cards_has_persons.search((where('person_id') == str(person_id)) & ((where('list_name') == str('В Работе'))))
        return query_result


    def get_curr_stage_percent(self, board_id, board_template):
        tasks_planned = self.local_cards.search((where('board_id') == str(board_id)) & (where('list_name') == str('Комплекс задач')))
        tasks_in_progress = self.local_cards.search((where('board_id') == str(board_id)) & (where('list_name') == str('В Работе')))
        tasks_on_hold = self.local_cards.search((where('board_id') == str(board_id)) & (where('list_name') == str('Согласование Выполнения')))
        tasks_done = self.local_cards.search((where('board_id') == str(board_id)) & (where('list_name') == str('Завершены')))

        if (len(tasks_planned) + len(tasks_in_progress) + len(tasks_on_hold) + len(tasks_done)) == 0:
            return 0
        else:
            return round((len(tasks_done) / (len(tasks_planned) + len(tasks_in_progress) + len(tasks_on_hold) + len(tasks_done))) * 100.0)


    def create_new_project(self, project_template, project_name = 'Новый проект', project_description = ''):        
        self.trello_client.add_board(board_name = project_name, source_board = None, organization_id = None, permission_level = 'private', default_lists=False)

        for board in self.trello_client.list_boards():
            if board.name == project_name:
                board.set_description(desc = project_description)

                for list_ in range(len(project_template)-1, -1, -1):
                    board.add_list(name = project_template[list_].get(list_), pos=None)
                
                for _list in board.list_lists():                        
                    for list_ in range(0, len(project_template)):
                        if _list.name == project_template[list_].get(list_):
                            for card in project_template[list_]['cards']:
                                _list.add_card(name = card, desc=None, labels=None, due="null", source=None, position=None, assign=None, keep_from_source="all")
                                print(f'{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}: [MSG] Card {card} was added')
                            break   


    def utc_to_local(self, utc_dt):
        return utc_dt.replace(tzinfo=timezone.utc, microsecond=0).astimezone(tz=None)


    def set_workhours(self, workhours = ['09:00:00', '18:00:00']):
        format_ = '%H:%M:%S'
        try:
            work_day_starts = datetime.strptime(workhours[0], format_).time()
            work_day_ends = datetime.strptime(workhours[1], format_).time()
        except Exception as err:
            print(f'{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}: [ERROR] {err}')
            pass
            #self.worktime.update({ 'work_day_starts': str(datetime.strptime('9:00:00', format_).time())})
            #self.worktime.update({ 'work_day_ends': str(datetime.strptime('18:00:00', format_).time())})
        else:
            if work_day_starts < work_day_ends:
                self.worktime.update({ 'work_day_starts': str(work_day_starts)})
                self.worktime.update({ 'work_day_ends': str(work_day_ends)})

                work_day_duration = timedelta(hours = work_day_ends.hour, minutes = work_day_ends.minute, seconds = work_day_ends.second) \
                                            - timedelta(hours = work_day_starts.hour, minutes = work_day_starts.minute, seconds = work_day_starts.second)
                
                self.worktime.update({ 'work_day_duration': str(work_day_duration)})

                self.calculate_work_hours()

            
    def get_workhours(self):
        return self.worktime.get(where('work_day_starts') != None)


    def set_lunch_hours(self, lunch_hours = ['13:00:00', '14:00:00']):
        format_ = '%H:%M:%S'
        try:
            lunch_hours_starts = datetime.strptime(lunch_hours[0], format_).time()
            lunch_hours_ends = datetime.strptime(lunch_hours[1], format_).time()
        except Exception as err:
            print(f'{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}: [ERROR] {err}')
            pass
        else:
            if lunch_hours_starts < lunch_hours_ends:     
                self.worktime.update({ 'lunch_hours_starts': str(lunch_hours_starts)})
                self.worktime.update({ 'lunch_hours_ends': str(lunch_hours_ends)})

                lunch_duration = timedelta(hours = lunch_hours_ends.hour, minutes = lunch_hours_ends.minute, seconds = lunch_hours_ends.second) \
                                            - timedelta(hours = lunch_hours_starts.hour, minutes = lunch_hours_starts.minute, seconds = lunch_hours_starts.second)
                
                self.worktime.update({ 'lunch_duration': str(lunch_duration)})
            
                self.calculate_work_hours()


    def get_lunch_hours(self):
        return self.worktime.get(where('lunch_hours_starts') != None)


    def calculate_work_hours(self):
        format_ = '%H:%M:%S'
        str_work_day_duration = self.worktime.get(where('work_day_duration') != None)['work_day_duration']
        str_lunch_duration = self.worktime.get(where('lunch_duration') != None)['lunch_duration']
        
        time_work_day_duration = datetime.strptime(str_work_day_duration, format_).time()
        time_lunch_duration = datetime.strptime(str_lunch_duration, format_).time()
        
        day_work_hours = timedelta(hours = time_work_day_duration.hour, minutes = time_work_day_duration.minute, seconds = time_work_day_duration.second) \
                                            - timedelta(hours = time_lunch_duration.hour, minutes = time_lunch_duration.minute, seconds = time_lunch_duration.second)
                
        self.worktime.update({ 'day_work_hours': str(day_work_hours)})

        work_days = self.worktime.get(where('work_days') != None)['work_days']

        week_work_hours = timedelta(seconds = int(work_days) * day_work_hours.total_seconds())
        self.worktime.update({ 'week_work_hours': str(week_work_hours)})


    def is_integer(self, n):
        try:
            float(n)
        except ValueError:
            return False
        else:
            return float(n).is_integer()


    def set_workdays(self, workdays = '5'):
        if self.is_integer(workdays):
            if (int(workdays) >= 1) and (int(workdays) <= 7):
                self.worktime.update({'work_days': str(workdays)})
        else:
            print(f'{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}: [ERROR] workdays not a number')


    def get_workdays(self):
        try:
            return ((self.worktime.get(where('work_days') != None))['work_days'])
        except:
            return '--:--'


    def set_database_update_period(self, update_period = '01:00:00'):
        format_ = '%H:%M:%S'
        try:
            update_period = datetime.strptime(update_period, format_).time()
        except Exception as err:
            pass
        else:     
            self.worktime.update({ 'update_period': str(update_period)})


    def get_update_period(self):
        try:
            return ((self.worktime.get(where('update_period') != None))['update_period'])
        except:
            return '--:--'


    def unify_time(self, datetime):
        return datetime.astimezone(self.local_timezone).replace(microsecond=0)


    def filter_work_hours(self, start_date, end_date):
        time_format = "%H:%M:%S"
        
        result_time = timedelta(hours=0, minutes=0, seconds=0)
        calculated_end_time = timedelta(hours=0, minutes=0, seconds=0)
        twelve_hours_delta = timedelta(hours=12, minutes=0)
        twenty_four_hours_delta = timedelta(hours=23, minutes=59, seconds=59)

        work_day_starts = self.worktime.get(where('work_day_starts') != None)['work_day_starts']
        work_day_ends = self.worktime.get(where('work_day_ends') != None)['work_day_ends']
        lunch_starts = self.worktime.get(where('lunch_hours_starts') != None)['lunch_hours_starts']
        lunch_ends = self.worktime.get(where('lunch_hours_ends') != None)['lunch_hours_ends']
        day_work_hours = self.worktime.get(where('day_work_hours') != None)['day_work_hours']

        work_day_starts = datetime.strptime(work_day_starts, time_format).time()
        work_day_ends = datetime.strptime(work_day_ends, time_format).time()
        lunch_starts = datetime.strptime(lunch_starts, time_format).time()
        lunch_ends = datetime.strptime(lunch_ends, time_format).time()
        day_work_hours = datetime.strptime(day_work_hours, time_format).time()

        while start_date <= end_date: 
            till_the_end_of_he_day_delta = twenty_four_hours_delta - timedelta(hours=start_date.hour, minutes=start_date.minute, seconds=start_date.second)
            calculated_end_time =  (start_date + till_the_end_of_he_day_delta)

            if calculated_end_time >= end_date:
                if calculated_end_time.time() > end_date.time():
                    calculated_end_time = end_date

            if start_date.weekday() < 5: #этот день не выходной // сделать параметром чтоб менять первый день недели
                if (calculated_end_time.time() < work_day_starts):#промежуток кончился раньше рабочего дня
                    pass

                elif (calculated_end_time.time() > work_day_starts) and (calculated_end_time.time() <= lunch_starts):#промежуток кончился после начала рабочего дня но раньше обеда:
                    
                    if start_date.time() <= work_day_starts:
                        result_time += timedelta(hours=calculated_end_time.hour, minutes=calculated_end_time.minute, seconds=calculated_end_time.second) - \
                                                    timedelta(hours=work_day_starts.hour, minutes=work_day_starts.minute, seconds=work_day_starts.second)

                    else:
                        result_time += timedelta(hours=calculated_end_time.hour, minutes=calculated_end_time.minute, seconds=calculated_end_time.second) - \
                                                    timedelta(hours=start_date.hour, minutes=start_date.minute, seconds=start_date.second)

                elif (calculated_end_time.time() > lunch_starts) and (calculated_end_time.time() < lunch_ends):#промежуток кончился после начала обеда но раньше конца обеда:
                    if start_date.time() <= work_day_starts:
                        result_time += timedelta(hours=lunch_starts.hour, minutes=lunch_starts.minute, seconds=lunch_starts.second) - \
                                                    timedelta(hours=work_day_starts.hour, minutes=work_day_starts.minute, seconds=work_day_starts.second)

                    elif (start_date.time() > work_day_starts) and (start_date.time() < lunch_starts):
                        result_time += timedelta(hours=lunch_starts.hour, minutes=lunch_starts.minute, seconds=lunch_starts.second) - \
                                                    timedelta(hours=start_date.hour, minutes=start_date.minute, seconds=start_date.second)

                    elif (start_date.time() >= lunch_starts):
                        pass

                elif (calculated_end_time.time() >= lunch_ends) and (calculated_end_time.time() < work_day_ends):#промежуток кончился после конца обеда но раньше конца дня
                    if start_date.time() <= work_day_starts:
                        result_time += (timedelta(hours=lunch_starts.hour, minutes=lunch_starts.minute, seconds=lunch_starts.second) - \
                                                    timedelta(hours=work_day_starts.hour, minutes=work_day_starts.minute, seconds=work_day_starts.second)) + \
                                                    (timedelta(hours=calculated_end_time.hour, minutes=calculated_end_time.minute, seconds=calculated_end_time.second) - \
                                                    timedelta(hours=lunch_ends.hour, minutes=lunch_ends.minute, seconds=lunch_ends.second))

                    elif (start_date.time() > work_day_starts) and (start_date.time() < lunch_starts):
                        result_time += (timedelta(hours=lunch_starts.hour, minutes=lunch_starts.minute, seconds=lunch_starts.second) - \
                                                    timedelta(hours=start_date.hour, minutes=start_date.minute, seconds=start_date.second)) + \
                                                    (timedelta(hours=calculated_end_time.hour, minutes=calculated_end_time.minute, seconds=calculated_end_time.second) - \
                                                    timedelta(hours=lunch_ends.hour, minutes=lunch_ends.minute, seconds=lunch_ends.second))     

                    elif (start_date.time() >= lunch_starts) and (start_date.time() < lunch_ends):
                        result_time += (timedelta(hours=calculated_end_time.hour, minutes=calculated_end_time.minute, seconds=calculated_end_time.second) - \
                                        timedelta(hours=lunch_ends.hour, minutes=lunch_ends.minute, seconds=lunch_ends.second)) 

                    elif (start_date.time() >= lunch_ends):
                        result_time += (timedelta(hours=calculated_end_time.hour, minutes=calculated_end_time.minute, seconds=calculated_end_time.second) - \
                                        timedelta(hours=start_date.hour, minutes=start_date.minute, seconds=start_date.second)) 

                elif (calculated_end_time.time() >= work_day_ends):#промежуток кончился позже рабочего дня
                    if start_date.time() <= work_day_starts:
                        result_time += timedelta(hours=day_work_hours.hour, minutes=day_work_hours.minute, seconds=day_work_hours.second)
                    
                    elif (start_date.time() > work_day_starts) and (start_date.time() < lunch_starts):
                        result_time += (timedelta(hours=lunch_starts.hour, minutes=lunch_starts.minute, seconds=lunch_starts.second) - \
                                                    timedelta(hours=start_date.hour, minutes=start_date.minute, seconds=start_date.second)) + \
                                                    (timedelta(hours=work_day_ends.hour, minutes=work_day_ends.minute, seconds=work_day_ends.second) - \
                                                    timedelta(hours=lunch_ends.hour, minutes=lunch_ends.minute, seconds=lunch_ends.second))  
                    
                    elif (start_date.time() >= lunch_starts) and (start_date.time() < lunch_ends):
                        result_time += (timedelta(hours=work_day_ends.hour, minutes=work_day_ends.minute, seconds=work_day_ends.second) - \
                                        timedelta(hours=lunch_ends.hour, minutes=lunch_ends.minute, seconds=lunch_ends.second))

                    elif (start_date.time() >= lunch_ends) and (start_date.time() <= work_day_ends):
                        result_time += (timedelta(hours=work_day_ends.hour, minutes=work_day_ends.minute, seconds=work_day_ends.second) - \
                                        timedelta(hours=start_date.hour, minutes=start_date.minute, seconds=start_date.second))

                    elif (start_date.time() > work_day_ends):
                        pass

            start_date += (till_the_end_of_he_day_delta + timedelta(minutes=1))

        return result_time

    
    def filter_reports_time(self, start_date, end_date, disable_filter = False):
        
        datetime_format = "%Y-%m-%d %H:%M:%S"
        filter_start_date = self.unify_time(datetime.strptime(self.filter_dates[0], datetime_format))
        filter_end_date = self.unify_time(datetime.strptime(self.filter_dates[1], datetime_format))

        result_time = timedelta(hours=0, minutes=0, seconds=0)

        if not disable_filter:

            #1
            if (start_date < filter_start_date) and (end_date < filter_start_date):
                return result_time
            #2
            elif (start_date < filter_start_date) and ((end_date > filter_start_date) and (end_date < filter_end_date)):
                start_date = filter_start_date

                return self.filter_work_hours(start_date = start_date, end_date = end_date)
            #3
            elif (start_date < filter_start_date) and (end_date > filter_end_date):
                start_date = filter_start_date
                end_date = filter_end_date

                return self.filter_work_hours(start_date = start_date, end_date = end_date)
            #4
            elif ((start_date > filter_start_date) and (start_date < filter_end_date)) and (end_date < filter_end_date):
                self.filter_work_hours(start_date = start_date, end_date = end_date)
            #5
            elif ((start_date > filter_start_date) and (start_date < filter_end_date)) and (end_date > filter_end_date):
                end_date = filter_end_date

                return self.filter_work_hours(start_date = start_date, end_date = end_date)
            #6
            elif (start_date > filter_end_date):
                return result_time
        
        else:
            #print("filter enabled!")
            return self.filter_work_hours(start_date = start_date, end_date = end_date)


    def get_card_stats_by_lists(self, card, disable_filter = False):
    
        board = self.trello_client.get_board(board_id = card.board_id)
        lists = board.list_lists()
        time_in_lists = {list_.id: {"time":timedelta(minutes=0)} for list_ in lists}

        ordered_list_movements = sorted(card.list_movements(), key=itemgetter("datetime"))

        if len(ordered_list_movements) == 0:

            time_in_lists[card.list_id]['time'] += self.filter_reports_time(start_date = card.created_date, end_date = self.unify_time(datetime.now()), disable_filter = disable_filter) #!!!!!!!
        
        elif len(ordered_list_movements) == 1:
            time_start = card.created_date
            time_end = self.unify_time(ordered_list_movements[0]['datetime'])
            list_id = ordered_list_movements[0]['source']['id']

            time_in_lists[list_id]['time'] += self.filter_reports_time(start_date = time_start, end_date = time_end, disable_filter = disable_filter)

            time_start = self.unify_time(ordered_list_movements[0]['datetime'])
            time_end = self.unify_time(datetime.now())
            list_id = ordered_list_movements[0]['destination']['id']

            time_in_lists[list_id]['time'] += self.filter_reports_time(start_date = time_start, end_date = time_end, disable_filter = disable_filter)

        else:

            for change_index in range(0, len(ordered_list_movements)):
                list_id = ordered_list_movements[change_index]['source']['id']

                if change_index == 0:

                    time_in_lists[list_id]['time'] += self.filter_reports_time(start_date = card.created_date, end_date = self.unify_time(ordered_list_movements[change_index]['datetime']), disable_filter = disable_filter)
                    
                elif change_index > 0:

                    time_start = ordered_list_movements[change_index - 1]['datetime']
                    time_end = ordered_list_movements[change_index]['datetime']

                    time_in_lists[list_id]['time'] += self.filter_reports_time(start_date = self.unify_time(time_start), end_date = self.unify_time(time_end), disable_filter = disable_filter)

                    if change_index + 1 == len(ordered_list_movements):

                        time_start = ordered_list_movements[change_index]['datetime']
                        time_end = datetime.now()

                        list_id = ordered_list_movements[change_index]['destination']['id']
                        time_in_lists[list_id]['time'] += self.filter_reports_time(start_date = self.unify_time(time_start), end_date = self.unify_time(time_end), disable_filter = disable_filter)

        return time_in_lists


    def get_project_report(self, board_id, lists, members):
        self.db.drop_table('report')
        for list_id in lists:
            for member_id in members:
                query_result = self.local_cards_has_persons.search((where('board_id') == str(board_id)) & (where('person_id') == str(member_id)))
                
                for result in query_result:
                    try:
                        card = self.trello_client.get_card(card_id = result['card_id'])
                        print(f'{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}: [MSG]: got card {result["card_name"], result["card_id"]}')
                    except Exception as err:
                        print(f'{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}: [ERROR]: {err}')
                    else:
                        card_lists_time = self.get_card_stats_by_lists(card = card)

                        for time in card_lists_time:
                            if time == list_id:
                                key = f'{time}'
                                if card_lists_time.get(key)['time'] > timedelta(minutes=1):
                                    list_name_query = self.local_lists.get((where('list_id') == str(time)))

                                    self.report.insert({ 'person_id': result['person_id'],
                                            'person_name': result['person_name'],
                                            'card_id': result['card_id'], 
                                            'card_name': result['card_name'], 
                                            'list_id': time,
                                            'list_name': list_name_query['list_name'],
                                            'list_time': str(card_lists_time.get(key)['time']),
                                            'board_id': result['board_id'],
                                            'board_name': result['board_name']}
                                    )


    def convert_seconds_to_readable_time(self, seconds): 
        min, sec = divmod(seconds, 60) 
        hour, min = divmod(min, 60) 
        return "%d:%02d:%02d" % (hour, min, sec) 
