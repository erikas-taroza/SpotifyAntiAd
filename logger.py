import time

class Logger:
    # If the file doesn't exist, then that means we don't want logging.
    can_log = False
    try:
        export = open("./log.txt", "r")
        if export != None:
            # Switch to write mode
            export.close()
            export = open("./log.txt", "a")
            export.write("\n********************************************************\n")
            (year, month, month_day, hour, minute, second, week_day, year_day, is_dst) = time.localtime()
            export.write(f"Log for: {month}/{month_day}/{year} {hour}:{minute}")
            export.write("\n********************************************************\n")
            export.close()
            can_log = True
    except FileNotFoundError:
        pass

    def log(message):
        if Logger.can_log:
            export = open("./log.txt", "a")
            print(message)
            export.write(message + "\n")
            export.close()