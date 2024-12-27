
class User:
    def __init__(self,name,password,type):
        self.name = name
        self.password = password
        self.type = type

class UserManager:
    def __init__(self):
        self.users = {
            "admin": User("admin","pass123","enterprise"),
            "user1": User("user1","pass123","individual"),
        }
    
    def check_user(self,name, password, type):
        if name in self.users.keys():
            user = self.users[name]
            if user.password == password and user.type == type:
                return True
        return False