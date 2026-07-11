from django.urls import include, path
from utilities.urls import get_model_urls

from . import views

app_label = 'netbox_ledger_tracker'


def _model_urls(segment, model_name):
    """Wire every view registered to ``model_name`` in NetBox's view registry.

    List/create/bulk views (``detail=False``) hang off ``<segment>/`` and the
    per-object views (``detail=True``: view, edit, delete, settle-up, plus the
    changelog and journal tabs NetBox auto-registers) hang off
    ``<segment>/<int:pk>/``.
    """
    return [
        path(f'{segment}/', include(get_model_urls(app_label, model_name, detail=False))),
        path(f'{segment}/<int:pk>/', include(get_model_urls(app_label, model_name))),
    ]


urlpatterns = [
    *_model_urls('currencies', 'currency'),
    *_model_urls('ledgers', 'ledger'),
    *_model_urls('people', 'person'),
    *_model_urls('expenses', 'expense'),
    *_model_urls('expense-parts', 'expensepart'),
    # Custom collection/detail views not attached via @register_model_view.
    path('expenses/split/add/', views.ExpenseSplitView.as_view(), name='expense_split_add'),
    path('expenses/<int:pk>/split/', views.ExpenseSplitView.as_view(), name='expense_split_edit'),
]
