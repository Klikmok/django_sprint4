"""Импорт функций, форм и моделей."""
from django.http import HttpResponse
from django.utils import timezone
from django.db.models import Count
from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import (
    DeleteView, DetailView, UpdateView, ListView
)
from django.urls import reverse_lazy
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError

from .forms import PostForm, CommentForm, UserForm
from .models import Post, Category, Comment


User = get_user_model()
POSTS_ON_PAGE = 10


def index(request):
    """Вью функция главной страницы."""
    posts_queryset = Post.objects.annotate(
        comment_count=Count('comments')
    ).filter(
        pub_date__lt=timezone.now(),
        is_published=True, category__is_published=True,
    ).order_by('-pub_date')
    posts_queryset[0].comment_count
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
        is_published=True
    )
    posts_queryset = Post.objects.annotate(
        comment_count=Count('comments')
    ).filter(
        pub_date__lt=timezone.now(),
        is_published=True,
        category__is_published=True,
        category__slug=category_slug
    ).order_by('-pub_date')
    paginator = Paginator(posts_queryset, POSTS_ON_PAGE)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'category': category,
        'page_obj': page_obj
    }
    return render(request, template, context)


class CategoryListView(ListView):
    """Вью класс для страницы отдельной категории."""

    template_name = 'blog/category.html'
    model = Post
    paginate_by = POSTS_ON_PAGE

    def get_context_data(self, **kwargs):
        """Получение контекста для страницы."""
        posts_queryset = Post.objects.annotate(
            comment_count=Count('comments')
        ).filter(
            pub_date__lt=timezone.now(),
            is_published=True,
            category__is_published=True,
            category__slug=self.kwargs['category_slug'],
        ).order_by('-pub_date')
        posts_queryset[0].comment_count
        category = get_object_or_404(
            Category.objects,
            slug=self.kwargs['category_slug'],
            is_published=True
        )
        context = super().get_context_data(**kwargs)
        context['pages_obj'] = posts_queryset
        context['category'] = category
        return context


class PostDetailView(DetailView):
    """Вью класс для страницы отдельного поста."""

    model = Post
    template_name = 'blog/detail.html'
    pk_url_kwarg = 'post_id'

    def get_context_data(self, **kwargs):
        """Получение контекста для страницы."""
        context = super().get_context_data(**kwargs)
        context['page_obj'] = Post.objects.filter(
            pub_date__lt=timezone.now(),
            is_published=True,
            category__is_published=True,
        )
        context['form'] = CommentForm()
        context['comments'] = (
            self.object.comments.filter(
            ).select_related('author')
        )
        return context


@login_required
def post_create(request):
    """Вью функция для формы создания поста."""
    template_name = 'blog/create.html'
    if request.POST:
        form = PostForm(
            request.POST or None,
            files=request.FILES or None
        )
        if form.is_valid():
            post = form.save(commit=False)
            post.author = request.user
            post.save()
            return redirect('blog:profile', request.user)
        else:
            raise ValidationError(
                'Составьте корректный пост, пожалуйста'
            )
    else:
        form = PostForm()
        context = {'form': form}
        return render(request, template_name, context)


class PostUpdateView(LoginRequiredMixin, UpdateView):
    """Вью класс для формы редактирования поста."""

    model = Post
    form_class = PostForm
    pk_url_kwarg = 'post_id'
    template_name = 'blog/create.html'

    def dispatch(self, request, *args, **kwargs):
        """Функция проверки формы."""
        get_object_or_404(
            Post,
            pk=kwargs['post_id'],
            is_published=True,
            author=request.user
        )
        return super().dispatch(request, *args, **kwargs)


class PostDeleteView(LoginRequiredMixin, DeleteView):
    """Вью класс для формы удаления поста."""

    model = Post
    pk_url_kwarg = 'post_id'
    template_name = 'blog/create.html'

    def dispatch(self, request, *args, **kwargs):
        """Функция проверки формы."""
        get_object_or_404(
            Post,
            pk=kwargs['post_id'],
            is_published=True,
            author=request.user
        )
        return super().dispatch(request, *args, **kwargs)

    def get_success_url(self):
        """Функция получения адреса."""
        return reverse_lazy(
            'blog:profile',
            kwargs={'username': self.request.user}
        )


@login_required
def add_comment(request, post_id):
    """Вью функция для формы создания комментария."""
    post = get_object_or_404(Post, pk=post_id)
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
        posts_queryset = Post.objects.annotate(
            comment_count=Count('comments')
        ).filter(
            author=author
        ).order_by('-pub_date')
    else:
        posts_queryset = Post.objects.annotate(
            comment_count=Count('comments')
        ).filter(
            pub_date__lt=timezone.now(),
            is_published=True,
            category__is_published=True,
            author=author
        ).order_by('-pub_date')
    paginator = Paginator(posts_queryset, POSTS_ON_PAGE)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    profile = get_object_or_404(
        User.objects.all(),
        username=username
    )
    template_name = 'blog/profile.html'
    context = {
        'page_obj': page_obj,
        'profile': profile
    }
    return render(request, template_name, context)


class ProfileUpdateView(LoginRequiredMixin, UpdateView):
    """Вью класс для формы редактирования профиля."""

    model = User
    form_class = UserForm
    template_name = 'blog/user.html'

    def dispatch(self, request, *args, **kwargs):
        """Функция проверки формы."""
        get_object_or_404(
            User,
            username=self.request.user.username,
        )
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form) -> HttpResponse:
        """Функция проверки и сохранения формы."""
        form.save()
        return super().form_valid(form)

    def get_success_url(self):
        """Функция получения адреса."""
        return reverse_lazy(
            'blog:profile',
            kwargs={'username': self.request.user}
        )

    def get_object(self):
        """Получение объекта пользователя для страницы."""
        return User.objects.get(username=self.request.user.username)


class CommentUpdateView(LoginRequiredMixin, UpdateView):
    """Вью класс для формы редактирования комментария."""

    model = Comment
    form_class = CommentForm
    pk_url_kwarg = 'comment_id'
    template_name = 'blog/comment.html'

    def dispatch(self, request, *args, **kwargs):
        """Функция проверки формы."""
        get_object_or_404(
            Post,
            pk=kwargs['post_id'],
            comments=kwargs['comment_id'],
            is_published=True
        )
        return super().dispatch(request, *args, **kwargs)

    def get_success_url(self):
        """Функция получения адреса."""
        return reverse_lazy(
            'blog:post_detail',
            kwargs={'post_id': self.object.post_id}
        )


class CommentDeleteView(LoginRequiredMixin, DeleteView):
    """Вью класс для формы удаления комментария."""

    model = Comment
    form_class = CommentForm
    template_name = 'blog/comment.html'
    pk_url_kwarg = 'comment_id'

    def dispatch(self, request, *args, **kwargs):
        """Функция проверки формы."""
        get_object_or_404(
            Post,
            pk=kwargs['post_id'],
            comments=kwargs['comment_id'],
            is_published=True
        )
        return super().dispatch(request, *args, **kwargs)

    def get_success_url(self):
        """Функция получения адреса."""
        return reverse_lazy(
            'blog:post_detail',
            kwargs={'post_id': self.object.post_id}
        )
