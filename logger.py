import time

class Logger:
    file = open("./log.txt", "a")
    file.write("\n********************************************************\n")
    (year, month, month_day, hour, minute, second, week_day, year_day, is_dst) = time.localtime()
    file.write(f"Log for: {month}/{month_day}/{year} {hour}:{minute}")
    file.write("\n********************************************************\n")
    file.close()

    def log(message, print_to_console = False):
        file = open("./log.txt", "a")
        file.write(message + "\n")
        file.close()
        if print_to_console:
            print(message)