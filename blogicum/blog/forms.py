from django import forms

from .models import Post, Category, Location, Comment


class PostForm(forms.ModelForm):
    """Форма для создания и редактирования публикаций."""

    category = forms.ModelChoiceField(
        label='Категория',
        queryset=Category.objects.filter(is_published=True),
    )
    location = forms.ModelChoiceField(
        label='Местоположение',
        queryset=Location.objects.filter(is_published=True),
        required=False,
    )

    class Meta:
        model = Post
        exclude = ['author']
        widgets = {
            'text': forms.Textarea(),
            'pub_date': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
        }


class CommentForm(forms.ModelForm):
    """Форма для создания комментариев к публикациям."""

    class Meta:
        model = Comment
        fields = ('text',)
