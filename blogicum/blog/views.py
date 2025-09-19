from django.contrib.auth.forms import UserChangeForm
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.models import User
from django.core.paginator import Paginator
from django.db.models import Count
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.views.generic import (
    CreateView,
    DeleteView,
    DetailView,
    ListView,
    UpdateView,
)

from .constants import POSTS_PER_PAGE
from .forms import CommentForm, PostForm
from .models import Category, Comment, Post


def get_post(
    posts=Post.objects,
    select_related=True,
    filter_published=True,
    annotate_comments=True
):
    """Возвращает QuerySet публикаций с возможностью гибкой настройки.

    Args:
        posts: исходный QuerySet (по умолчанию Post.objects)
        select_related: подкачивать связанные объекты
            (author, category, location)
        filter_published: фильтровать только опубликованные посты
        annotate_comments: добавлять количество комментариев к постам

    Returns:
        QuerySet: Отфильтрованный и отсортированный QuerySet публикаций
    """
    if select_related:
        posts = posts.select_related('author', 'category', 'location')
    if filter_published:
        posts = posts.filter(
            is_published=True,
            pub_date__lte=timezone.now(),
            category__is_published=True
        )
    order_by = Post._meta.ordering
    if annotate_comments:
        posts = posts.annotate(comment_count=Count('comments'))
    return posts.order_by(*order_by)


def paginate_queryset(request, queryset, posts_per_page=POSTS_PER_PAGE):
    return Paginator(
        queryset,
        posts_per_page
    ).get_page(request.GET.get('page'))


class PostAuthorRequiredMixin(UserPassesTestMixin):
    """Доступ только автору поста."""

    def test_func(self):
        return self.request.user == self.get_object().author

    def handle_no_permission(self):
        post = self.get_object()
        return redirect('blog:post_detail', post_id=post.id)


class CommentAuthorRequiredMixin(UserPassesTestMixin):
    """Доступ только автору комментария."""

    def test_func(self):
        return self.request.user == self.get_object().author

    def handle_no_permission(self):
        comment = self.get_object()
        return redirect('blog:post_detail', post_id=comment.post.id)


class IndexView(ListView):
    """Главная страница: список публикаций."""

    model = Post
    template_name = 'blog/index.html'
    context_object_name = 'page_obj'
    paginate_by = POSTS_PER_PAGE
    queryset = get_post()


class CategoryPostsView(ListView):
    """Посты по выбранной категории."""

    model = Post
    template_name = 'blog/category.html'
    context_object_name = 'page_obj'
    paginate_by = POSTS_PER_PAGE

    def get_category(self):
        """Возвращает объект категории или 404."""
        return get_object_or_404(
            Category,
            slug=self.kwargs['category_slug'],
            is_published=True
        )

    def get_queryset(self):
        category = self.get_category()
        return get_post(posts=category.posts.all())

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['category'] = self.get_category()
        return context


class PostDetailView(DetailView):
    """Детальная страница поста."""

    model = Post
    template_name = 'blog/detail.html'
    context_object_name = 'post'
    pk_url_kwarg = 'post_id'

    def get_object(self, queryset=None):
        post = super().get_object(queryset)
        if self.request.user != post.author:
            return get_object_or_404(
                get_post(filter_published=True),
                pk=post.pk
            )
        return post

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form'] = CommentForm()
        context['comments'] = (
            self.object.comments.all()
            .order_by('created_at')  # тесты требуют явно указать порядок
        )
        return context


class CreatePostView(LoginRequiredMixin, CreateView):
    """Создание новой публикации."""

    model = Post
    template_name = 'blog/create.html'
    form_class = PostForm

    def form_valid(self, form):
        self.object = form.save(commit=False)
        self.object.author = self.request.user
        return super().form_valid(form)

    def get_success_url(self):
        return reverse(
            'blog:profile',
            kwargs={'username': self.request.user.username}
        )


class EditPostView(PostAuthorRequiredMixin, UpdateView):
    """Редактирование публикации (только автор)."""

    model = Post
    template_name = 'blog/create.html'
    form_class = PostForm
    pk_url_kwarg = 'post_id'

    def form_valid(self, form):
        self.object = form.save(commit=False)
        self.object.save()
        return super().form_valid(form)

    def get_success_url(self):
        return reverse(
            'blog:post_detail',
            args=[self.kwargs[self.pk_url_kwarg]]
        )


class DeletePostView(PostAuthorRequiredMixin, DeleteView):
    """Удаление публикации (только автор)."""

    model = Post
    pk_url_kwarg = 'post_id'
    template_name = 'blog/detail.html'
    success_url = reverse_lazy('blog:index')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        post = self.get_object()
        context['confirm_delete'] = True
        context['form'] = CommentForm()
        context['object'] = post
        return context


class EditCommentView(CommentAuthorRequiredMixin, UpdateView):
    """Редактирование комментария (только автор)."""

    model = Comment
    form_class = CommentForm
    template_name = 'blog/comment.html'
    pk_url_kwarg = 'comment_id'

    def get_success_url(self):
        return reverse(
            'blog:post_detail',
            kwargs={'post_id': self.kwargs.get('post_id')}
        )


class DeleteCommentView(CommentAuthorRequiredMixin, DeleteView):
    """Удаление комментария (только автор)."""

    model = Comment
    template_name = 'blog/comment.html'
    pk_url_kwarg = 'comment_id'

    def get_success_url(self):
        return reverse(
            'blog:post_detail',
            args=[self.kwargs[self.pk_url_kwarg]]
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['confirm_delete'] = True
        return context


class AddCommentView(LoginRequiredMixin, CreateView):
    """Добавление комментария к посту."""

    model = Comment
    form_class = CommentForm
    template_name = 'blog/comment_form.html'

    def form_valid(self, form):
        form.instance.author = self.request.user
        form.instance.post = get_object_or_404(
            Post,
            id=self.kwargs['post_id']
        )
        return super().form_valid(form)

    def get_success_url(self):
        return reverse(
            'blog:post_detail',
            args=[self.kwargs['post_id']]
        )

    def get(self, request, *args, **kwargs):
        return redirect(
            'blog:post_detail',
            post_id=self.kwargs['post_id']
        )


class ProfileView(ListView):
    """Профиль пользователя: список его публикаций."""

    model = Post
    template_name = 'blog/profile.html'
    context_object_name = 'page_obj'
    paginate_by = POSTS_PER_PAGE

    def get_author(self):
        """Возвращает автора профиля или 404."""
        return get_object_or_404(
            User,
            username=self.kwargs['username']
        )

    def get_queryset(self):
        author = self.get_author()
        return get_post(
            posts=author.posts.all(),
            filter_published=self.request.user != author
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['profile'] = self.get_author()
        return context


class EditProfileView(LoginRequiredMixin, UpdateView):
    """Редактирование профиля пользователя."""

    model = User
    form_class = UserChangeForm
    template_name = 'blog/user.html'

    def get_object(self):
        return self.request.user

    def get_success_url(self):
        return reverse(
            'blog:profile',
            args=[self.request.user.username]
        )
