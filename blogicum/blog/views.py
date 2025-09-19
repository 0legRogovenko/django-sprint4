from django.db.models import Count
from django.contrib.auth.forms import UserChangeForm
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.models import User
from django.core.paginator import Paginator
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


def get_post_queryset(
    posts=Post.objects,
    select_related=True,
    filter_published=True,
):
    """Возвращает QuerySet публикаций с возможностью гибкой настройки.

    Args:
        posts: исходный QuerySet (по умолчанию Post.objects)
        select_related: подкачивать связанные объекты
            (author, category, location)
        filter_published: фильтровать только опубликованные посты

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
    order_by = Post._meta.ordering or ['-pub_date']
    return posts.annotate(comment_count=Count('comments')).order_by(*order_by)


def paginate_queryset(request, queryset, posts_per_page=POSTS_PER_PAGE):
    paginator = Paginator(queryset, posts_per_page)
    page_number = request.GET.get('page')
    return paginator.get_page(page_number)


class AuthorRequiredMixin(UserPassesTestMixin):
    """Проверяет, что пользователь является автором объекта."""

    def test_func(self):
        return self.request.user == self.get_object().author

    def handle_no_permission(self):
        if hasattr(self, 'get_object'):
            object = self.get_object()
            if isinstance(object, Post):
                return redirect('blog:post_detail', post_id=object.id)
            if isinstance(object, Comment):
                return redirect('blog:post_detail', post_id=object.post.id)
        return redirect('blog:index')


class IndexView(ListView):
    """Главная страница: список публикаций."""

    model = Post
    template_name = 'blog/index.html'
    context_object_name = 'page_obj'
    paginate_by = POSTS_PER_PAGE
    queryset = get_post_queryset()


class CategoryPostsView(ListView):
    """Посты по выбранной категории."""

    model = Post
    template_name = 'blog/category.html'
    context_object_name = 'page_obj'
    paginate_by = POSTS_PER_PAGE

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['category'] = self.category
        return context

    def get_queryset(self):
        self.category = get_object_or_404(
            Category, slug=self.kwargs['category_slug'], is_published=True
        )
        category_posts = self.category.posts.all()
        return get_post_queryset(posts=category_posts)


class PostDetailView(DetailView):
    """Детальная страница поста."""

    model = Post
    template_name = 'blog/detail.html'
    context_object_name = 'post'
    pk_url_kwarg = 'post_id'

    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        if self.request.user != obj.author:
            published_posts = get_post_queryset()
            obj = get_object_or_404(published_posts, pk=obj.pk)
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
        self.object = form.save(commit=False)
        self.object.author = self.request.user
        self.object.save()
        return super().form_valid(form)

    def get_success_url(self):
        username = self.request.user.username
        return reverse('blog:profile', kwargs={'username': username})


class EditPostView(AuthorRequiredMixin, UpdateView):
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
        return reverse('blog:post_detail', kwargs={'post_id': self.object.id})


class DeletePostView(AuthorRequiredMixin, DeleteView):
    """Удаление публикации (только автор)."""

    model = Post
    pk_url_kwarg = 'post_id'
    template_name = 'blog/detail.html'
    success_url = reverse_lazy('blog:index')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        obj = self.get_object()
        context['confirm_delete'] = True
        context['form'] = CommentForm()
        context['object'] = obj
        return context


class EditCommentView(AuthorRequiredMixin, UpdateView):
    """Редактирование комментария (только автор)."""

    model = Comment
    form_class = CommentForm
    template_name = 'blog/comment.html'
    pk_url_kwarg = 'comment_id'

    def get_success_url(self):
        post_id = self.kwargs.get('post_id')
        return reverse('blog:post_detail', kwargs={'post_id': post_id})


class DeleteCommentView(AuthorRequiredMixin, DeleteView):
    """Удаление комментария (только автор)."""

    model = Comment
    template_name = 'blog/comment.html'
    pk_url_kwarg = 'comment_id'

    def get_success_url(self):
        post = self.get_object().post
        return reverse('blog:post_detail', kwargs={'post_id': post.id})

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
        post_id = self.kwargs.get('post_id')
        post = get_object_or_404(Post, id=post_id)
        form.instance.author = self.request.user
        form.instance.post = post
        return super().form_valid(form)

    def get_success_url(self):
        post_id = self.kwargs.get('post_id')
        return reverse('blog:post_detail', kwargs={'post_id': post_id})

    def get(self, request, *args, **kwargs):
        return redirect('blog:post_detail', post_id=self.kwargs.get('post_id'))


class ProfileView(ListView):
    """Профиль пользователя: список его публикаций."""

    model = Post
    template_name = 'blog/profile.html'
    context_object_name = 'page_obj'
    paginate_by = POSTS_PER_PAGE

    def get_queryset(self):
        username = self.kwargs.get('username')
        profile_user = get_object_or_404(User, username=username)
        self.profile_user = profile_user

        if self.request.user == profile_user:
            posts = profile_user.posts.all()
            filter_published = False
        else:
            posts = profile_user.posts.filter(is_published=True)
            filter_published = True

        return get_post_queryset(
            posts=posts,
            filter_published=filter_published,
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
        kwargs = {'username': self.request.user.username}
        return reverse('blog:profile', kwargs=kwargs)
