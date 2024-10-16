# Django's authentication system을 사용하기 위한 custom user class
class CustomUser:
    def __init__(self, user_info):
        self.user_id = user_info['user_id']
        self.email = user_info['email']
        self.full_name = user_info.get('full_name', '')
        self.oauth_provider = user_info.get('oauth_provider', '')
        self.is_active = True
        self.is_authenticated = True

    def __str__(self):
        return self.email

    @property
    def is_anonymous(self):
        return False

    @property
    def is_staff(self):
        return False