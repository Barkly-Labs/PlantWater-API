import time
import os


class Logger:


    def __init__(
        self,
        filename="garden.log",
        max_lines=500
    ):

        self.filename = filename
        self.max_lines = max_lines



    def _timestamp(self):

        t = time.localtime()

        return (
            "{:04d}-{:02d}-{:02d} "
            "{:02d}:{:02d}:{:02d}"
        ).format(
            t[0],
            t[1],
            t[2],
            t[3],
            t[4],
            t[5]
        )



    def _write(
        self,
        level,
        message
    ):

        line = (
            "[{}] [{}] {}\n"
        ).format(
            self._timestamp(),
            level,
            message
        )


        # Serial output

        print(
            line,
            end=""
        )


        # Save to flash

        try:

            with open(
                self.filename,
                "a"
            ) as f:

                f.write(line)



            self._trim()



        except Exception as e:

            print(
                "Logger error:",
                e
            )





    def _trim(self):

        """
        Keep log size under control
        """

        try:

            with open(
                self.filename,
                "r"
            ) as f:

                lines = f.readlines()



            if len(lines) > self.max_lines:


                lines = lines[
                    -self.max_lines:
                ]


                with open(
                    self.filename,
                    "w"
                ) as f:

                    f.writelines(lines)



        except:

            pass





    def info(
        self,
        message
    ):

        self._write(
            "INFO",
            message
        )





    def warning(
        self,
        message
    ):

        self._write(
            "WARN",
            message
        )





    def error(
        self,
        message
    ):

        self._write(
            "ERROR",
            message
        )





    def clear(self):

        try:

            os.remove(
                self.filename
            )

        except:

            pass