from django.db import models
class Problem(models.Model):
    problem_id=models.CharField(max_length=50,primary_key=True)
    problem_index=models.CharField(max_length=50, blank=True, default="")
    problem_name=models.CharField(max_length=200)
    contest_id=models.CharField(max_length=50)
    category = models.CharField(max_length=50, blank=True)
    difficulty=models.FloatField(null=True,blank=True)
    is_experimental=models.BooleanField(default=False)
    updated_at=models.DateTimeField(auto_now=True)
    display_difficulty=models.FloatField(null=True, blank=True)
    def __str__(self):
        return self.problem_name


class Contest(models.Model):
    contest_id = models.CharField(max_length=100, primary_key=True)
    title = models.CharField(max_length=300)
    start_epoch_second = models.BigIntegerField(default=0)
    duration_second = models.BigIntegerField(default=0)
    rate_change = models.CharField(max_length=50, blank=True, default="-")
    series = models.CharField(max_length=30, default="OTHER")
    contest_format = models.CharField(max_length=20, default="ALGORITHM")
    is_evergreen = models.BooleanField(default=False)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title


class ContestProblem(models.Model):
    contest = models.ForeignKey(
        Contest,
        on_delete=models.CASCADE,
        related_name="contest_problems",
    )
    problem = models.ForeignKey(
        Problem,
        on_delete=models.CASCADE,
        related_name="contest_problems",
    )
    problem_index = models.CharField(max_length=50, blank=True, default="")

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["contest", "problem"],
                name="unique_contest_problem",
            )
        ]
        ordering = ["problem_index", "problem_id"]

    def __str__(self):
        return f"{self.contest_id}: {self.problem_index}"


class Tag(models.Model):
    name=models.CharField(max_length=25,unique=True)
    is_default=models.BooleanField(default=False)
    created_by=models.ForeignKey(
        'accounts.CustomUser',
        on_delete=models.SET_NULL,
        null=True,blank=True,

    )
    def __str__(self):
        return self.name

class Log(models.Model):
    user=models.ForeignKey(
        'accounts.CustomUser',
        on_delete=models.CASCADE,
    )
    problem = models.ForeignKey(Problem, on_delete=models.CASCADE)
    submitted_contest_id=models.CharField(max_length=50)
    is_correct=models.BooleanField(default=False)
    first_ac_date=models.DateTimeField(null=True,blank=True)
    last_submitted_date=models.DateTimeField()
    tags=models.ManyToManyField(Tag,blank=True)
    created_at=models.DateTimeField(auto_now_add=True)
    updated_at=models.DateTimeField(auto_now=True)
    memo = models.TextField(blank=True, default="")
    do_later = models.BooleanField(default=False)
    def __str__(self):
        return self.problem.problem_name
    class Meta():
        unique_together = [("user", "problem")]


class ContestAttempt(models.Model):
    user = models.ForeignKey(
        'accounts.CustomUser',
        on_delete=models.CASCADE,
    )
    problem = models.ForeignKey(Problem, on_delete=models.CASCADE)
    submitted_contest_id = models.CharField(max_length=100)
    is_correct = models.BooleanField(default=False)
    first_ac_date = models.DateTimeField(null=True, blank=True)
    last_submitted_date = models.DateTimeField()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "problem", "submitted_contest_id"],
                name="unique_user_problem_contest_attempt",
            )
        ]

    def __str__(self):
        return f"{self.user.username} - {self.submitted_contest_id} - {self.problem_id}"

class DoLater(models.Model):
    user = models.ForeignKey('accounts.CustomUser', on_delete=models.CASCADE)
    problem = models.ForeignKey(Problem, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [("user", "problem")]

    def __str__(self):
        return f"{self.user.username} - {self.problem.problem_name}"
