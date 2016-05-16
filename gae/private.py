
# private entries for gae flask main app

# allowed users, authenticated by google
# not very scalable and should be moved to data store

white_list = ['tom.a.ryan@gmail.com',
              'thos.a.ryan@gmail.com',
              'maylin.ryan@gmail.com',
              'ryan.christine@gmail.com',
              'ryan.stephanie@gmail.com'
              ]

# ised by Flask session
flask_secret = 'My Flask Application Secret'

# internal to main app, not GAE admin
# admin can clear images, etc.

admin_name = 'tom'
admin_password = 'ryan'

