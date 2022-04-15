class Logger:
    # If the file doesn't exist, then that means we don't want logging.
    can_log = False
    try:
        open("./log.txt", "r")
        can_log = True
    except FileNotFoundError:
        can_log = False
        pass

    def log(message):
        if Logger.can_log:
            export = open("./log.txt", "a")
            print(message)
            export.write(message + "\n")
            export.close()