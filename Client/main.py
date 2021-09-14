#!/usr/bin/python
from kivy.uix.boxlayout import BoxLayout
from kivy.core.text.markup import MarkupLabel
from kivymd.uix.selectioncontrol import MDCheckbox
from kivy.uix.floatlayout import FloatLayout
from kivymd.uix.textfield import MDTextField
from kivy.properties import ObjectProperty
from kivy.properties import ListProperty
from kivy.uix.widget import Widget
from kivymd.uix.snackbar import Snackbar
from kivymd.uix.dialog import MDDialog
from kivymd.uix.list import OneLineListItem, TwoLineListItem, TwoLineAvatarIconListItem, IRightBodyTouch, BaseListItem
from kivy.uix.screenmanager import ScreenManager, Screen, SwapTransition, SlideTransition
from kivy.clock import Clock
from kivy.uix.bubble import Bubble, BubbleButton

from collections import defaultdict
import chat_client

from kivymd.app import MDApp

server_ip = '127.1.1.1'
server_port = 2020

class ChatBubble(MDTextField):
    """Class to represent chat bubbles in the app """
    def __init__(self,username,message,**kwargs):
        super().__init__(**kwargs)
        self.hint_text = username
        self.text = message
        self.readonly = True


class RightCheckbox(IRightBodyTouch,MDCheckbox):
    """Custom right container"""



def emptyfunc(*args,**kwargs): pass #Used for testing

def show_error(error,title='Error'):
    """Shows an error to the user in a dialogue box"""
    dialogue = MDDialog(
        title=title, size_hint=(.5, .3), text_button_ok='Okay',
        text=str(error),
        events_callback=emptyfunc)
    dialogue.open()

def show_message(message):
    """Shows a message notification in the bottom corner of the screen"""
    message_bar = Snackbar(text=message,duration = 1)
    message_bar.show()

    

class LoginPage(Screen):
    """Class to represent the login screen"""
    remember = False
    screen_manager = ObjectProperty()
    screen1 = ObjectProperty()
    screen2 = ObjectProperty()
    screen3 = ObjectProperty()
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def login_btn(self,username,password):
        """Button clicked by user to log in"""
        if username.strip() == '' or password.strip() == '': #No data entered
            show_error('Please enter your details to login')
            return
        #Send a request to connect to the server
        result = chat_client.connect(server_ip,server_port,username,password,new_account='False', error_callback=show_error)
        if result:
            #We are connected
            if self.remember == True:
                #The user has asked to be remembered, note their details
                with open('details.txt','w') as f:
                    f.write(f'{username}${password}')
            #Launch the main page with a logged in account
            chat_app.create_main_page(username,new_account=False)
        elif result == False:
            #Invalid credentials were given
            show_error('Incorrect username or password, please try again')
    
    def create_btn(self,username,password1,password2,fname,lname,email):
        """Button pressed when creating account"""
        #Button pressed by user to create account
        if password1.strip() == '' or password2.strip() == '': #No password given
            show_error('Please enter your details to create an account')
            return
        elif password1 != password2: #Passwords don't match
            show_error('Passwords do not match')
            return
        #Connect to the client with a new account
        result = chat_client.connect(server_ip,server_port,username,fname,lname,email,password1,new_account='True', error_callback=show_error)
        if result:
            #Create messages and requests for the user
            with open(f'{username}_messages.txt','w'):
                pass
            with open(f'{username}_requests.txt','w'):
                pass
            #Launch main page
            chat_app.create_main_page(username,new_account=True)
        else:
            show_error('This username already exists')
    

    def validate_page1(self,username,email):
        """Validation for the first page"""
        if username.strip() == '' or email.strip() == '': #No data entered
            show_error('Please enter a username and email to continue') 
        elif ' ' in username or ' ' in email: #Spaces in data
            show_error('Username and email must not contain spaces')
        elif '$' in username: #This is reserved for the server
            show_error('Username must not contain a $')
        elif len(username) > 16: #Helps to save space
            show_error('Username must be less than 16 characters')
        else:
            #Validation passed, go to next page
            self.screen_manager.switch_to(self.screen2,transition=SlideTransition(direction='left'))

    def validate_page2(self,fname,lname):
        """Validation for the second page"""
        if fname.strip() == '' or lname.strip() == '': #No data entered
            show_error('Please enter your name to continue')
        elif ' ' in fname or ' ' in lname: #Name contains spaces
            show_error('Names must not contain spaces')
        elif len(fname) > 16 or len(lname) > 16: #Helps to save space
            show_error('Names must be less than 16 characters')
        else:
            #Validation passed, go to next page
            self.screen_manager.switch_to(self.screen3,transition=SlideTransition(direction='left'))


class MainPage(Screen):
    """Main page of the app to send messages"""
    header = ObjectProperty()
    message = ObjectProperty()
    def __init__(self,new_account,**kwargs):
        super().__init__(**kwargs)
        self.username = chat_app.username
        self.save_messages = False
        if new_account:
            #Show a welcome message for new account members
            show_error(f'Hey there {self.username}, welcome to Splinter. Tap the add contact button to start chatting', title='Welcome')
        self.message_count = defaultdict(int)
        #Format app title
        chat_app.title = f'{chat_app.default_title} - {self.username}'
        self.to_username = ''
        #Get user contacts
        contacts = chat_client.send_server_request(f'$4 {self.username}',show_error,python_object = True)
        self.contacts = {}
        #Get user messages
        messages = chat_client.send_server_request(f'$3 {self.username}',show_error, python_object = True)
        #Start listening for messages
        chat_client.start_listening(self.recive_notification,show_error)
        #Loop through incoming messages that have been stored
        for message in messages:
            if message[0] == '$server fw':
                #Notify a friend request has been recieved, go to next message
                self.add_request(*message[1].split(' '))
                continue
            message[1] = message[1].strip()
            #Increase message count for the user
            self.message_count[message[0]] += 1
            #Write the message so it can be opened
            with open(f'{self.username}_messages.txt','a') as f: 
                f.write(f'{message[0]},{message[1]}\n')
        #Loop through contacts and add them with their respective message counts
        for contact in contacts:
            self.contacts[contact[0]] = (contact[1],contact[2])
            name = f'{contact[1]} {contact[2]}'
            if contact[0] in self.message_count:
                name = f'{name} ({self.message_count[contact[0]]})'
            self.ids.contact_list.add_widget(TwoLineListItem(text = name, secondary_text = contact[0], on_release=self.chat))
    
    def show_diaglouge(self,title,message, etype):
        """Show a diaglouge box to the user"""
        #Is this for logging out or clearing messages
        if etype == 'clear_messages':
            events_callback = self.response_for_clear_messages
        elif etype == 'logout':
            events_callback = self.response_for_logout
        #Create and open the dialouge box in the middle of the screen
        dialog = MDDialog(
        title=title, size_hint=(.5, .3), 
        text_button_ok='Yes', 
        text_button_cancel= 'Cancel',
        text=str(message),
        events_callback=events_callback)
        dialog.open()

    def response_for_clear_messages(self,response, instance):
        """If yes, clear messages"""
        if response == 'Yes':
            with open(f'{self.username}_messages.txt','w') as f:
                f.write('')
    
    def response_for_logout(self,response,instance):
        """If yes, log the user out"""
        if response == 'Yes':
            chat_app.backlog()

    def chat(self,instance):
        """Swtich to chat screen"""
        self.to_username = instance.secondary_text
        self.ids.screen_manager.current = 'chat'

    def on_chat_opened(self):
        #Set the title to username
        self.header.title = self.contacts[self.to_username][0]
        #Open the chat screen
        self.ids.screen_manager.transition = SlideTransition(direction = 'right')
        #Read each message and add it
        with open(f'{self.username}_messages.txt','r') as f:
            for line in f.readlines():
                line = line.split(',')
                l1,l2 = line[0], ','.join(line[1:])
                self.recive_message(l1,l2)
        try:
            #Scrolls to the last message sent
            self.ids.scroll.scroll_to(self.ids.message_board.children[0])
        except IndexError:
            pass

    def on_main_opened(self):
        #Opens the main page and re adds the contacts
        self.ids.screen_manager.transition = SlideTransition(direction='left')
        self.ids.contact_list.clear_widgets()
        for username,name in self.contacts.items():
            name = ' '.join(name)
            if self.message_count[username] != 0:
                name = f'{name} ({self.message_count[contact]})'
            self.ids.contact_list.add_widget(TwoLineListItem(text = name, secondary_text = username, on_release=self.chat))

    def testfunc(self,instance):
        pass

    def update_contact(self,username):
        """Update a users message count if a new message has been recieved"""
        print('Username = ',username)
        for widget in self.ids.contact_list.children:
            #Find the user
            temp_text = widget.secondary_text
            if temp_text == username:
                #Increase message count
                self.message_count.get(username,0)+1
                #Change name to reflect
                self.message_count[username] = self.message_count.get(username,0) + 1
                widget.text = '{} {} ({})'.format(*self.contacts[username],self.message_count[username])

    def remove_contact(self,instance):
        """Experimental"""

    def recive_notification(self,username,message):
        """Message recieved from server"""
        #Parse the request
        if username == '$server':
            if message == '3':
                show_message('Friend request sent')
            elif message == '1':
                show_error('User does not exists, please try again')
            elif message == '2':
                show_error('You are already friends')
            return
        elif username == '$server fw':
            self.add_request(*message.split(' '))
            return
        message = message.strip()
        #Add the message to storage
        with open(f'{self.username}_messages.txt','a') as f:
            f.write(f'{username},{message}\n')
        #If we are on the chat with the user already, add it to the board
        if username == self.to_username and self.ids.screen_manager.current == 'chat':
            self.ids.message_board.add_widget(ChatBubble(username=self.contacts[username][0], message = message))
        else:
            #Otherwise, update the message count for the user
            show_message(f'New message from {self.contacts[username][0]}')
            self.update_contact(username)
    
    def recive_message(self,username,message):
        if username == f'Me_{self.to_username}': #Add my message to the message board
            username = 'Me'
            self.ids.message_board.add_widget(ChatBubble(username=username, message = message))
        elif username == self.to_username: #Otherwise add the user's
            self.ids.message_board.add_widget(
                ChatBubble(username = username, message = message)
                )

    def add_request(self,username,fname,lname):
        #Shows the user they have a friend request
        show_message(f'Friend request received from {username}')
        with open(f'{self.username}_requests.txt','a') as f:
            f.write(f'{username} {fname} {lname}')
        #Notifys them they can accept
        self.ids.request_list.add_widget(TwoLineListItem(text=f'{username} ({fname} {lname})',secondary_text='Click to accept',on_release = self.accept_request, on_hold = self.deny_request))

    def accept_request(self,instance):
        #Remove friend request count
        temp_text = instance.text.replace('(','')
        temp_text = temp_text.replace(')','')
        username,fname,lname = temp_text.split(' ')
        #Tell the server to accept the request
        chat_client.send_server_request(f'$2 {username}',show_error,er=False)
        #Remove them from the request list
        self.ids.request_list.remove_widget(instance)
        #Add as contact
        self.contacts[username] = [fname,lname]

    def deny_request(self,instance):
        #Remove from request list but don't accept
        self.ids.request_list.remove_widget(instance)
        show_message('Request denied')


    def add_contact(self):
        #Process friend request send
        username = self.ids.username.text
        if not username.strip(): #No data entered
            show_error('Please enter a username')
            self.ids.username.text = ''
            return
        #Send the request
        chat_client.send_server_request(f'$1 {username}',show_error,er=False)
        #Clear the message box
        self.ids.username.text = ''

    def send_message(self):
        if self.message.text.strip() == '': #No data entered
            show_error('Please enter a message to send!')
            return
        #Send the message with the username and message
        chat_client.send(self.to_username,f' {self.message.text}')
        usr = f'Me_{self.to_username}'
        #Save message to storage
        with open(f'{self.username}_messages.txt','a') as f:
            f.write(f'{usr},{self.message.text}\n')
        #Add message to board
        self.recive_message(usr,self.message.text)
        #Clear text
        self.message.text = ''


    def back(self):
        #Go back to main screen and reset message count for given user
        self.message_count[self.to_username] = 0
        self.ids.screen_manager.current = 'main'
        self.ids.screen_manager.transition = SlideTransition(direction = 'left')
        self.ids.message_board.clear_widgets() #Saves computing power

    def clear_messages(self):
        #Show warning message for clearing message
        self.show_diaglouge('Warning','This will only clear the messages for you, are you sure?', etype = 'clear_messages')

    def switch_screen(self,screen,direction= 'left'):
        #Switch to a given screen
        self.ids.screen_manager.transition = SlideTransition(direction=direction)
        self.ids.screen_manager.current = screen


    def logout(self):
        #Log the user out with a warning
        with open('details.txt','w') as f:
            f.write('')
        self.show_diaglouge('Warning','Are you sure?','logout')


class MainApp(MDApp):
    def __init__(self,**kwargs):
        self.default_title = "Splinter" #Set the app name
        self.title = self.default_title
        self.icon = 'icon.png' #Set the app icon
        super().__init__(**kwargs)

    def build(self):
        """Method called by kivy to build the app"""
        #Set default themes
        self.theme_cls.primary_palette = "Yellow"
        self.theme_cls.theme_style = "Dark"
        self.screen_manager = ScreenManager(transition=SwapTransition())
        #Create and launch the login page
        self.login_page = LoginPage(name='login')
        self.screen_manager.add_widget(self.login_page)
        #Read user details
        with open('details.txt','r') as f:
            data = f.read()
        if not data:
            pass
        else:
            #If there are some, process and send a login request
            username,password = data.split('$')
            result = chat_client.connect(server_ip,server_port,username,password,new_account='False',error_callback=show_error)
            self.username = username
            self.create_main_page(username,new_account=False)
        return self.screen_manager

    def create_main_page(self,username,new_account):
        #Creates the main contact page
        self.username = username
        self.main_page = MainPage(new_account,name = 'contact')
        self.screen_manager.add_widget(self.main_page)
        self.screen_manager.current = 'contact'
        self.screen_manager.remove_widget(self.login_page)

    def backlog(self):
        #Logs the user out and returns them to the login page
        self.login_page = LoginPage(name='login')
        self.screen_manager.add_widget(self.login_page)
        self.screen_manager.current = 'login'
        chat_client.close()
        self.screen_manager.remove_widget(self.main_page)
        self.title = self.default_title


    
    def callback(self):
        """Testing method"""
        pass


if __name__ == '__main__':
    chat_app = MainApp()
    chat_app.run()