from django import forms
from django_summernote.widgets import SummernoteWidget


def singleton_page_admin_form_factory(model_class):
    """ModelForm с Summernote для поля content (страницы «О нас», контакты и т.д.)."""
    class SingletonPageForm(forms.ModelForm):
        class Meta:
            model = model_class
            fields = ["title", "content"]
            widgets = {"content": SummernoteWidget()}

    SingletonPageForm.__name__ = f"{model_class.__name__}AdminForm"
    return SingletonPageForm
