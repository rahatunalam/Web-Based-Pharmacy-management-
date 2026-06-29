from django.db import models

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