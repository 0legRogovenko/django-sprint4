from django import forms

from .models import Post, Category, Location, Comment


class PostForm(forms.ModelForm):
    """Форма для создания и редактирования публикаций."""

    class Meta:
        model = Post
        exclude = ['author']
        widgets = {
            'pub_date': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
        }


class CommentForm(forms.ModelForm):
    """Форма для создания комментариев к публикациям."""

    class Meta:
        model = Comment
        fields = ('text',)
