from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

# Create your models here.
class Medicine(models.Model):
    name = models.CharField(max_length=150)
    company = models.CharField(max_length=150)
    product_type = models.CharField(max_length=50)
    quantity = models.PositiveBigIntegerField()
    price_per_unit = models.DecimalField(max_digits=10,decimal_places=2)
    total_price = models.DecimalField(max_digits=10,decimal_places=2)

    def __str__(self):
        return self.name
    
class Sale(models.Model):
    medicine = models.ForeignKey(
        Medicine,
        on_delete= models.CASCADE,
        related_name='sale'
    )
    salesman = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='sales'
    )
    quantity_sold = models.PositiveIntegerField()
    price_per_unit = models.DecimalField(max_digits=10, decimal_places=2)
    item_total = models.DecimalField(max_digits=10, decimal_places=2)
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    discount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    final_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    sold_at = models.DateTimeField(default=timezone.now)
    def __str__(self):
        return f"{self.medicine.name} x {self.quantity_sold} — {self.sold_at.date()}"