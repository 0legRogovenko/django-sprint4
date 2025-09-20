
from django.contrib.auth import get_user_model
from django.db import models

from blog.constants import MAX_TITLE_LENGTH

User = get_user_model()


class TimestampedModel(models.Model):
    """Базовая модель с общими полями."""

    is_published = models.BooleanField(
        default=True,
        verbose_name='Опубликовано',
        help_text='Снимите галочку, чтобы скрыть публикацию.'
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Добавлено'
    )

    class Meta:
        abstract = True


class Category(TimestampedModel):
    """Модель категории для публикаций."""

    title = models.CharField(
        max_length=256,
        verbose_name='Заголовок'
    )
    description = models.TextField(
        verbose_name='Описание'
    )
    slug = models.SlugField(
        unique=True,
        verbose_name='Идентификатор',
        help_text=(
            'Идентификатор страницы для URL; разрешены символы латиницы, '
            'цифры, дефис и подчёркивание.'
        ),
    )

    class Meta:
        verbose_name = 'категория'
        verbose_name_plural = 'Категории'
        ordering = ('title',)

    def __str__(self) -> str:
        """Возвращает строковое представление категории."""
        return self.title[:MAX_TITLE_LENGTH]


class Location(TimestampedModel):
    """Модель местоположения публикации."""

    name = models.CharField(
        max_length=256,
        verbose_name='Название места'
    )

    class Meta:
        verbose_name = 'местоположение'
        verbose_name_plural = 'Местоположения'
        ordering = ('name',)

    def __str__(self) -> str:
        """Возвращает строковое представление местоположения."""
        return self.name


class Post(TimestampedModel):
    """Модель публикации в блоге."""

    title = models.CharField(
        max_length=256,
        verbose_name='Заголовок'
    )
    text = models.TextField(
        verbose_name='Текст'
    )
    pub_date = models.DateTimeField(
        verbose_name='Дата и время публикации',
        help_text=(
            'Если установить дату и время в будущем — можно делать отложенные '
            'публикации.'
        ),
    )
    image = models.ImageField(
        upload_to='post_images/',
        blank=True,
        null=True,
        verbose_name='Изображение',
    )
    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        verbose_name='Автор публикации',
        related_name='posts',
    )
    location = models.ForeignKey(
        Location,
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        verbose_name='Местоположение',
    )
    category = models.ForeignKey(
        Category,
        null=True,
        on_delete=models.SET_NULL,
        verbose_name='Категория',
    )

    class Meta:
        default_related_name = 'posts'
        ordering = ('-pub_date',)
        verbose_name = 'публикация'
        verbose_name_plural = 'Публикации'

    def __str__(self) -> str:
        """Возвращает строковое представление публикации."""
        return self.title[:MAX_TITLE_LENGTH]


class CommentManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().order_by('created_at')


class Comment(TimestampedModel):
    """
    Модель комментария к публикации.

    Attributes:
        post: Публикация, к которой относится комментарий
    """

    post = models.ForeignKey(
        Post,
        on_delete=models.CASCADE,
        verbose_name='Публикация',
    )
    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        verbose_name='Автор комментария',
    )
    text = models.TextField(
        verbose_name='Текст комментария',
    )
    objects = CommentManager()

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'комментарий'
        verbose_name_plural = 'Комментарии'
        default_related_name = 'comments'
