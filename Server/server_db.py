import sqlite3

def login_check(username,password):
    """Checks if the user exists in the database with the given username and password"""
    conn=sqlite3.connect('Userbase.db')
    c=conn.cursor()
    c.execute("SELECT * FROM User WHERE username=? and password =?",(username,password,))
    user_info = c.fetchall()
    conn.close()
    if user_info == []:
        return False
    else:
        return True

def create_user(*details):
    """Creates a new user in the database"""
    conn=sqlite3.connect('Userbase.db')
    c=conn.cursor()
    c.execute("SELECT * FROM User WHERE username=?",(details[0],))
    if c.fetchall() != []: #If the user already exists, return false
        conn.close()
        return False
    #Otherwise create a new entry
    c.execute("INSERT INTO User(username,first_name,last_name,email,password) VALUES(?,?,?,?,?)",(details))
    conn.commit()
    conn.close()
    return True

def get_contacts(username):
    #Returns the friends of a given user
    conn=sqlite3.connect('Userbase.db')
    c=conn.cursor()
    c.execute("SELECT contact2, User.first_name, User.last_name FROM Contacts INNER JOIN User ON Contacts.contact2 = User.username WHERE contact1=?",(username,))
    list1 = c.fetchall()
    c.execute("SELECT contact1, User.first_name, User.last_name FROM Contacts INNER JOIN User ON Contacts.contact1 = User.username WHERE contact2=?",(username,))
    list2 = c.fetchall()
    conn.close()  
    return list1+list2



def user_exists(user):
    #Checks if a given user is in the database
    conn=sqlite3.connect('Userbase.db')
    c=conn.cursor()
    c.execute("SELECT username FROM User WHERE username=?",(user,))
    if c.fetchall() == []:
        conn.close()
        return False
    else:
        conn.close()
        return True

def contact_check(user1,user2):
    #Checks if two users are friends
    conn=sqlite3.connect('Userbase.db')
    c=conn.cursor()
    c.execute("SELECT * FROM Contacts WHERE (contact1 = ? AND contact2 = ?) OR (contact1 = ? AND contact2 = ?)",(user1,user2,user2,user1))
    if c.fetchall() == []:
        conn.close()
        return True
    else:
        conn.close()
        return False

def add_contact(user1,user2):
    #Adds a given pair of contacts so they are friends
    conn=sqlite3.connect('Userbase.db')
    c=conn.cursor()
    c.execute("INSERT INTO Contacts (contact1,contact2) VALUES (?,?)",(user1,user2))
    conn.commit()
    conn.close()

def get_name(username):
    #Returns the first and last name of a given user
    conn=sqlite3.connect('Userbase.db')
    c=conn.cursor()
    c.execute("SELECT first_name, last_name FROM User WHERE username = ?",(username,))
    t = c.fetchall()[0]
    conn.commit()
    conn.close()
    return '{} {}'.format(*t)

