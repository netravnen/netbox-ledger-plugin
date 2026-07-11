from netbox.api.routers import NetBoxRouter

from . import views

app_name = 'netbox_ledger_tracker'

router = NetBoxRouter()
router.register('currencies', views.CurrencyViewSet)
router.register('ledgers', views.LedgerViewSet)
router.register('people', views.PersonViewSet)
router.register('expenses', views.ExpenseViewSet)
router.register('expense-parts', views.ExpensePartViewSet)

urlpatterns = router.urls
