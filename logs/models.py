from django.db import models
class Problem(models.Model):
    problem_id=models.CharField(max_length=50,primary_key=True)
    problem_name=models.CharField(max_length=200)
    contest_id=models.CharField(max_length=50)
    difficulty=models.FloatField(null=True,blank=True)
    is_experimental=models.BooleanField(default=False)
    updated_at=models.DateTimeField(auto_now=True)
    display_difficulty=models.FloatField(null=True, blank=True)
    def __str__(self):
        return self.problem_name
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
    def __str__(self):
        return self.problem.problem_name
    class Meta():
        unique_together = [("user", "problem")]
