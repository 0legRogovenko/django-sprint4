from django.db.models import Count

from django.contrib.auth.forms import UserChangeForm, UserCreationForm
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.models import User
from django.core.paginator import Paginator
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.views.generic import (
    CreateView,
    DeleteView,
    DetailView,
    ListView,
    UpdateView,
    View,
)

from .forms import CommentForm, PostForm
from .models import Category, Comment, Post
PAGINATE_BY = 10


def get_post_queryset(
    qs=None,
    select_related=True,
    filter_published=True,
):
    """
    Возвращает QuerySet публикаций с возможностью гибкой настройки.
    qs: исходный QuerySet (по умолчанию Post.objects)
    select_related: подкачивать связанные объекты (author, category, location)
    filter_published: фильтровать только опубликованные посты
    """
    if qs is None:
        qs = Post.objects
    if select_related:
        qs = qs.select_related('author', 'category', 'location')
    if filter_published:
        qs = qs.filter(
            is_published=True,
            pub_date__lte=timezone.now(),
            category__is_published=True
        )
    qs = qs.annotate(comment_count=Count('comments')).order_by('-pub_date')
    return qs


def paginate_queryset(request, queryset, per_page=10):
    paginator = Paginator(queryset, per_page)
    page_number = request.GET.get('page')

    page_obj = paginator.get_page(page_number)
    return page_obj


class IndexView(ListView):
    """Главная страница: список публикаций."""

    model = Post
    template_name = 'blog/index.html'
    context_object_name = 'page_obj'
    paginate_by = 10

    def get_queryset(self):
        return get_post_queryset()


class CategoryPostsView(ListView):
    """Посты по выбранной категории."""

    model = Post
    template_name = 'blog/category.html'
    context_object_name = 'page_obj'
    paginate_by = 10

    def get_queryset(self):
        self.category = get_object_or_404(
            Category, slug=self.kwargs['category_slug'], is_published=True
        )
        return get_post_queryset().filter(category=self.category)


class PostDetailView(DetailView):
    """Детальная страница поста."""

    model = Post
    template_name = 'blog/detail.html'
    context_object_name = 'post'
    pk_url_kwarg = 'post_id'

    def get_object(self, queryset=None):
        if queryset is None:
            queryset = get_post_queryset()

        pk = self.kwargs.get(self.pk_url_kwarg)
        if pk is None:
            raise AttributeError(
                f"Generic detail view {self.__class__.__name__} "
                f"must be called with either an object pk or "
                f"a slug in the URLconf."
            )

        obj = get_object_or_404(Post, pk=pk)

        if self.request.user != obj.author:
            if (
                not obj.is_published
                or not obj.category.is_published
                or obj.pub_date > timezone.now()
            ):
                raise Http404('Пост недоступен')

        return obj

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form'] = kwargs.get('form', CommentForm())
        context['comments'] = self.object.comments.all().order_by('created_at')
        return context


class CreatePostView(LoginRequiredMixin, CreateView):
    """Создание новой публикации."""

    model = Post
    template_name = 'blog/create.html'
    form_class = PostForm

    def form_valid(self, form):
        form.instance.author = self.request.user
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('blog:profile', kwargs={
                       'username': self.request.user.username})


class EditPostView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    """Редактирование публикации (только автор)."""

    model = Post
    template_name = 'blog/create.html'
    form_class = PostForm
    pk_url_kwarg = 'post_id'

    def test_func(self):
        return self.request.user == self.get_object().author

    def handle_no_permission(self):
        return redirect('blog:post_detail', post_id=self.get_object().id)

    def get_success_url(self):
        return reverse('blog:post_detail', kwargs={'post_id': self.object.id})


class DeletePostView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    """Удаление публикации (только автор)."""

    model = Post
    pk_url_kwarg = 'post_id'
    template_name = 'blog/detail.html'
    success_url = reverse_lazy('blog:index')

    def test_func(self):
        return self.request.user == self.get_object().author

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['confirm_delete'] = True
        context['form'] = CommentForm()
        return context


class EditCommentView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    """Редактирование комментария (только автор)."""

    model = Comment
    form_class = CommentForm
    template_name = 'blog/comment.html'
    pk_url_kwarg = 'comment_id'

    def test_func(self):
        return self.request.user == self.get_object().author

    def get_success_url(self):
        return reverse('blog:post_detail', kwargs={
                       'post_id': self.get_object().post.id})


class DeleteCommentView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    """Удаление комментария (только автор)."""

    model = Comment
    template_name = 'blog/comment.html'
    pk_url_kwarg = 'comment_id'

    def test_func(self):
        return self.request.user == self.get_object().author

    def get_success_url(self):
        return reverse('blog:post_detail', kwargs={
                       'post_id': self.get_object().post.id})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['confirm_delete'] = True
        return context


class AddCommentView(LoginRequiredMixin, View):
    """Добавление комментария к посту."""

    def post(self, request, post_id):
        post = get_object_or_404(Post, id=post_id)
        form = CommentForm(request.POST)
        if form.is_valid():
            comment = form.save(commit=False)
            comment.author = request.user
            comment.post = post
            comment.save()
        return redirect('blog:post_detail', post_id=post.id)

    def get(self, request, post_id):
        """Если кто-то зайдёт GET-запросом — просто редиректим на пост."""
        return redirect('blog:post_detail', post_id=post_id)


class ProfileView(ListView):
    """Профиль пользователя: список его публикаций."""

    model = Post
    template_name = 'blog/profile.html'
    context_object_name = 'page_obj'
    paginate_by = 10

    def get_queryset(self):
        self.profile_user = get_object_or_404(
            User, username=self.kwargs['username'])
        return get_post_queryset(
            qs=self.profile_user.posts.all(),
            filter_published=False
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['profile'] = self.profile_user
        return context


class EditProfileView(LoginRequiredMixin, UpdateView):
    """Редактирование профиля пользователя."""

    model = User
    form_class = UserChangeForm
    template_name = 'blog/user.html'

    def get_object(self):
        return self.request.user

    def get_success_url(self):
        return reverse('blog:profile', kwargs={
                       'username': self.request.user.username})


class RegisterView(CreateView):
    """Регистрация нового пользователя."""

    model = User
    form_class = UserCreationForm
    template_name = 'registration/registration_form.html'
    success_url = reverse_lazy('login')
