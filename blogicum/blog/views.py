"""Импорт функций, форм и моделей."""
from django.http import HttpResponseRedirect
from django.db.models import Count
from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import (
    DeleteView, DetailView, UpdateView
)
from django.urls import reverse_lazy, reverse
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.contrib.auth import get_user_model

from .constants import POSTS_ON_PAGE, now
from .forms import PostForm, CommentForm, UserForm
from .models import Post, Category, Comment


User = get_user_model()


def get_comment_object(**kwargs):
    """Получение объекта комментария."""
    return get_object_or_404(
        Comment,
        pk=kwargs['comment_id'],
        post=kwargs['post_id'],
        post__is_published=True,
    )


def get_post_object(author=None):
    """Получение объекта поста."""
    post = Post.objects.annotate(
        comment_count=Count('comments')
    ).filter(
        pub_date__lte=now,
        is_published=True, category__is_published=True,
    ).order_by('-pub_date')
    if author:
        post.filter(author=author)
    return post


def get_user_object(self):
    """Проверка пользователя."""
    return get_object_or_404(
        User,
        username=self.request.user,
    )


def index(request):
    """Вью функция главной страницы."""
    posts_queryset = get_post_object()
    paginator = Paginator(posts_queryset, POSTS_ON_PAGE)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    context = {
        'page_obj': page_obj
    }
    template = 'blog/index.html'
    return render(request, template, context)


def category_posts(request, category_slug):
    """Вью функция для странциы категории."""
    template = 'blog/category.html'
    category = get_object_or_404(
        Category.objects,
        slug=category_slug,
        is_published=True,
    )
    posts_queryset = get_post_object().filter(
        category__slug=category.slug
    )
    paginator = Paginator(posts_queryset, POSTS_ON_PAGE)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'category': category,
        'page_obj': page_obj
    }
    return render(request, template, context)


class PostDetailView(DetailView):
    """Вью класс для страницы отдельного поста."""

    model = Post
    template_name = 'blog/detail.html'
    pk_url_kwarg = 'post_id'

    def get_context_data(self, **kwargs):
        """Получение данных для страницы."""
        context = super().get_context_data(**kwargs)
        context['form'] = CommentForm()
        context['comments'] = self.object.comments.select_related('author')
        return context

    def get_object(self):
        """Получение объекта для вью класса."""
        post_author = super().get_object()
        if self.request.user == post_author.author:
            return post_author
        return get_object_or_404(
            Post,
            is_published=True,
            category__is_published=True,
            pub_date__lte=now,
            id=self.kwargs['post_id'],
        )


@login_required
def post_create(request):
    """Вью функция для формы создания поста."""
    template_name = 'blog/create.html'
    form = PostForm(
        request.POST or None,
        files=request.FILES or None,
    )
    if form.is_valid():
        post = form.save(commit=False)
        post.author = request.user
        post.save()
        return redirect('blog:profile', request.user)
    context = {'form': form}
    return render(request, template_name, context)


class PostUpdateView(UpdateView):
    """Вью класс для формы редактирования поста."""

    model = Post
    form_class = PostForm
    pk_url_kwarg = 'post_id'
    template_name = 'blog/create.html'

    def dispatch(self, request, *args, **kwargs):
        """Функция проверки формы."""
        if self.get_object().author != self.request.user:
            return redirect('blog:post_detail', post_id=self.kwargs['post_id'])
        get_post_object().filter(author=self.request.user)
        return super().dispatch(request, *args, **kwargs)

    def get_object(self):
        """Получение объекта поста для страницы."""
        return get_object_or_404(
            Post, pk=self.kwargs['post_id'], is_published=True,
        )

    def get_success_url(self):
        """Функция получения адреса."""
        return reverse_lazy(
            'blog:post_detail',
            kwargs={'post_id': self.get_object().pk},
        )


class PostDeleteView(DeleteView):
    """Вью класс для формы удаления поста."""

    model = Post
    pk_url_kwarg = 'post_id'
    template_name = 'blog/create.html'

    def dispatch(self, request, *args, **kwargs):
        """Функция проверки формы."""
        if self.get_object().author != request.user:
            return redirect('blog:post_detail', post_id=self.kwargs['post_id'])

        get_object_or_404(
            Post,
            pk=kwargs['post_id'],
            author=self.request.user,
        )
        return super().dispatch(request, *args, **kwargs)

    def get_object(self):
        """Получение объекта поста для страницы."""
        return get_object_or_404(
            Post, pk=self.kwargs['post_id'], is_published=True,
        )

    def get_success_url(self):
        """Функция получения адреса."""
        return reverse_lazy(
            'blog:profile',
            kwargs={'username': self.request.user}
        )


@login_required
def add_comment(request, post_id):
    """Вью функция для формы создания комментария."""
    post = get_object_or_404(Post, pk=post_id, is_published=True,)
    form = CommentForm(request.POST)
    if form.is_valid():
        comment = form.save(commit=False)
        comment.author = request.user
        comment.post = post
        comment.save()
    return redirect('blog:post_detail', post_id)


def profile(request, username):
    """Вью функция для страницы пользователя."""
    author = get_object_or_404(User, username=username)
    if author == request.user:
        posts_queryset = Post.objects.filter(
            author=author
        ).order_by('-pub_date').annotate(
            comment_count=Count('comments')
        )
    else:
        posts_queryset = get_post_object(author)
    paginator = Paginator(posts_queryset, POSTS_ON_PAGE)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    profile = get_object_or_404(
        User,
        username=username,
    )
    template_name = 'blog/profile.html'
    context = {
        'page_obj': page_obj,
        'profile': profile,
    }
    return render(request, template_name, context)


class ProfileUpdateView(LoginRequiredMixin, UpdateView):
    """Вью класс для формы редактирования профиля."""

    model = User
    form_class = UserForm
    template_name = 'blog/user.html'

    def dispatch(self, request, *args, **kwargs):
        """Функция проверки формы."""
        get_user_object(self)
        return super().dispatch(request, *args, **kwargs)

    def get_success_url(self):
        """Функция получения адреса."""
        return reverse_lazy(
            'blog:profile',
            kwargs={'username': self.request.user}
        )

    def get_object(self):
        """Получение объекта пользователя для страницы."""
        return get_user_object(self)


class CommentUpdateView(LoginRequiredMixin, UpdateView):
    """Вью класс для формы редактирования комментария."""

    model = Comment
    form_class = CommentForm
    pk_url_kwarg = 'post_id'
    template_name = 'blog/comment.html'

    def dispatch(self, request, *args, **kwargs):
        """Функция проверки формы."""
        if request.GET and self.get_object().author != self.request.user:
            return HttpResponseRedirect(
                reverse('blog:post_detail', self.kwargs['post_id'])
            )
        get_comment_object(**kwargs)
        return super().dispatch(request, *args, **kwargs)

    def get_success_url(self):
        """Функция получения адреса."""
        return reverse_lazy(
            'blog:post_detail',
            kwargs={'post_id': self.object.post_id}
        )

    def get_object(self):
        """Получение объекта пользователя."""
        return get_object_or_404(
            Comment,
            post=self.kwargs['post_id'],
            pk=self.kwargs['comment_id'],
            post__is_published=True,
            author=User.objects.get(username=self.request.user),
        )


class CommentDeleteView(LoginRequiredMixin, DeleteView):
    """Вью класс для формы удаления комментария."""

    model = Comment
    form_class = CommentForm
    pk_url_kwarg = 'post_id'
    template_name = 'blog/comment.html'

    def dispatch(self, request, *args, **kwargs):
        """Функция проверки формы."""
        if request.GET and self.get_object().author != self.request.user:
            return HttpResponseRedirect(
                reverse('blog:post_detail', self.kwargs['post_id'])
            )
        get_comment_object(**kwargs)
        return super().dispatch(request, *args, **kwargs)

    def get_success_url(self):
        """Функция получения адреса."""
        return reverse_lazy(
            'blog:post_detail',
            kwargs={'post_id': self.object.post_id}
        )

    def get_object(self):
        """Получение объекта пользователя."""
        return get_object_or_404(
            Comment,
            post=self.kwargs['post_id'],
            pk=self.kwargs['comment_id'],
            post__is_published=True,
            author=User.objects.get(username=self.request.user),
        )
