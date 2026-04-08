from django.contrib import admin
from solo.admin import SingletonModelAdmin

from .models import RobotsTxt


@admin.register(RobotsTxt)
class RobotsTxtAdmin(SingletonModelAdmin):
    fields = ["content"]
