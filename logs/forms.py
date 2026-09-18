from django import forms

from .models import Goal


GOAL_CONTEST_TYPE_CHOICES = [
    ("EVERGREEN", "常設"),
    ("ALGORITHM", "アルゴリズム"),
    ("GRAND", "グランド"),
    ("HEURISTIC", "ヒューリスティック"),
]


class GoalForm(forms.ModelForm):
    contest_types = forms.MultipleChoiceField(
        label="挑戦するコンテストの種類",
        choices=GOAL_CONTEST_TYPE_CHOICES,
        widget=forms.CheckboxSelectMultiple,
    )

    class Meta:
        model = Goal
        fields = [
            "title",
            "start_date",
            "end_date",
            "contest_types",
            "difficulty_min",
            "difficulty_max",
            "target_count",
        ]
        labels = {
            "title": "目標名",
            "start_date": "開始日",
            "end_date": "終了日",
            "difficulty_min": "難易度（下限）",
            "difficulty_max": "難易度（上限）",
            "target_count": "目標問題数",
        }
        widgets = {
            "start_date": forms.DateInput(attrs={"type": "date"}),
            "end_date": forms.DateInput(attrs={"type": "date"}),
            "difficulty_min": forms.NumberInput(attrs={"min": 0, "step": 1}),
            "difficulty_max": forms.NumberInput(attrs={"min": 0, "step": 1}),
            "target_count": forms.NumberInput(attrs={"min": 1, "step": 1}),
        }

    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get("start_date")
        end_date = cleaned_data.get("end_date")
        difficulty_min = cleaned_data.get("difficulty_min")
        difficulty_max = cleaned_data.get("difficulty_max")

        if start_date and end_date and start_date > end_date:
            self.add_error("end_date", "終了日は開始日以降にしてください。")
        if (
            difficulty_min is not None
            and difficulty_max is not None
            and difficulty_min > difficulty_max
        ):
            self.add_error(
                "difficulty_max",
                "難易度の上限は下限以上にしてください。",
            )
        return cleaned_data
