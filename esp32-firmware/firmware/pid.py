class PIDController:

    def __init__(
        self,
        kp,
        ki,
        kd,
        target,
        integral_limit=800,
        deadzone=25
    ):

        self.kp = kp
        self.ki = ki
        self.kd = kd

        self.target = target

        self.integral = 0
        self.last_error = 0

        self.integral_limit = integral_limit
        self.deadzone = deadzone



    def compute(self, current):

        error = current - self.target


        # close enough
        if abs(error) < self.deadzone:
            return 0


        # already wet
        if error < 0:
            return 0



        self.integral += error


        # anti-windup
        self.integral = max(
            -self.integral_limit,
            min(
                self.integral,
                self.integral_limit
            )
        )


        derivative = (
            error -
            self.last_error
        )


        self.last_error = error



        output = (
            self.kp * error
            +
            self.ki * self.integral
            +
            self.kd * derivative
        )


        return max(
            0,
            output
        )