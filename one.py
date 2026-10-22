def validate(username,password):
    usernames = []
    passwords = []

    u_s = {
        1:{
            username : "Amir",
            password : "1234"
        },
        2:{
            username : "illya",
            password : "1234",
        }
    }
    if username == "Amir" and password=="1234":
        print("welcome")
