from django.shortcuts import render,redirect,get_object_or_404
from django.contrib.auth import authenticate,login,logout
from django.contrib.auth.decorators import login_required
from django.db.models import Sum,Count,F
from django.db.models.functions import TruncMonth,TruncYear
from django.template import context
from django.utils import timezone
from django.contrib.auth.models import User
from django.contrib import messages
from .forms import LoginForm
from .models import Medicine,Sale,Wholesale,Purchase
from datetime import timedelta,date
import calendar
import json

# Create your views here.
# Login view
def login_view(request):
    form = LoginForm()

    if request.method == "POST":
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request,username=username,password=password)

        if user is not None:
            login(request,user)

            # Admin redirect
            if user.is_superuser:
                return redirect('pharmacy:dashboard')
            else:
                return redirect('pharmacy:sale_medicines')
        
        return render( request,"pharmacy/login.html",{"error": "Invalid username or password"})
        
    return render(request, 'pharmacy/login.html')

@login_required
def dashboard(request):
    # ── KPI Cards ──────────────────────────────────────────

    # Total revenue from all sales (final price after discount)
    total_sales = float(Sale.objects.aggregate(total=Sum('final_price'))['total'] or 0
)
    # Total stock value (quantity × price per unit for every medicine)
    total_stock_value = float(Medicine.objects.aggregate(total=Sum(F('quantity')*F('price_per_unit')))['total'] or 0)

    # Net profit = revenue - stock cost
    net_profit = total_sales - total_stock_value

    # Count medicines with quantity below 10
    low_stock_count = Medicine.objects.filter(quantity__lt = 10).count()

    # ── Donut Chart — stock distribution by medicine ────────
    # Groups sold quantity by medicine name
    distribution_qs = Sale.objects.values('medicine__name').annotate(units=Sum('quantity_sold')).order_by('-units')[:6]

    distribution_chart = {
        'labels': [row['medicine__name'] for row in distribution_qs],
        'values': [row['units'] for row in distribution_qs],
    }

    # ── Bar Chart — monthly sale quantity ───────────────────
    monthly_sales_qs = Sale.objects.annotate(month=TruncMonth('sold_at')).values('month').annotate(units=Sum('quantity_sold')).order_by('month')
    monthly_chart={
        'labels': [row['month'].strftime('%b %Y') for row in monthly_sales_qs],
        'values': [row['units'] for row in monthly_sales_qs],
    }

    # ── Line Chart — yearly revenue trend ──────────────────
    yearly_qs = Sale.objects.annotate(year=TruncYear('sold_at')).values('year').annotate(revenue=Sum('final_price')).order_by('year')
    yearly_chart = {
        'labels': [row['year'].strftime('%Y') for row in yearly_qs],
        'values': [float(row['revenue']) for row in yearly_qs],
    }

    # ── Low stock medicines for the alert card ──────────────
    low_stock_items = Medicine.objects.filter(quantity__lt=10).order_by('quantity')

    # ── Top selling medicines ───────────────────────────────
    top_medicines = Sale.objects.values('medicine__name').annotate(units=Sum('quantity_sold')).order_by('-units')[:5]

    context = {
        'total_sales':       total_sales,
        'total_stock_value': total_stock_value,
        'net_profit':        net_profit,
        'low_stock_count':   low_stock_count,
        'low_stock_items':   low_stock_items,
        'top_medicines':     top_medicines,

        # Serialize to JSON so Chart.js can read them in the template
        'distribution_chart': json.dumps(distribution_chart),
        'monthly_chart':      json.dumps(monthly_chart),
        'yearly_chart':       json.dumps(yearly_chart),
    }
    return render(request,'pharmacy/index.html',context)

# Logout view
def logout_view(request):
    logout(request)
    return redirect('pharmacy:login') # redirct to login function

# Add Medicine
@login_required
def add_medicine(request):

    if request.method == 'POST':
        total_count = int(request.POST.get('total_count',0))

        for i in range(total_count):
            name = request.POST.get(f'medicine_{i}_name')
            company = request.POST.get(f'medicine_{i}_company')
            type_ = request.POST.get(f'medicine_{i}_type')
            quantity = request.POST.get(f'medicine_{i}_quantity')
            price = request.POST.get(f'medicine_{i}_price')
            total_price = request.POST.get(f'medicine_{i}_total_price')

            if name and type_ and quantity and price:
                quantity= int(quantity)
                price =  float(price)
                 
                medicine = Medicine.objects.create(
                    name=name,
                    company=company, 
                    product_type=type_,
                    quantity=int(quantity),
                    price_per_unit=float(price),
                    total_price =float(total_price)
                )

                Purchase.objects.create(
                    medicine=medicine,
                    company=company or '',
                    quantity=quantity,
                    price_per_unit=price,
                    total_cost=quantity * price,
                    added_by=request.user,
                )
        return redirect('pharmacy:add_medicine')
                 
    return render(request,'pharmacy/add-medicine.html')

@login_required
def s_add_medicine(request):

    if request.method == 'POST':
        total_count = int(request.POST.get('total_count',0))

        for i in range(total_count):
            name = request.POST.get(f'medicine_{i}_name')
            company = request.POST.get(f'medicine_{i}_company')
            type_ = request.POST.get(f'medicine_{i}_type')
            quantity = request.POST.get(f'medicine_{i}_quantity')
            price = request.POST.get(f'medicine_{i}_price')
            total_price = request.POST.get(f'medicine_{i}_total_price')

            if name and type_ and quantity and price:
                 Medicine.objects.create(
                    name=name,
                    company=company, 
                    product_type=type_,
                    quantity=int(quantity),
                    price_per_unit=float(price),
                    total_price =float(total_price)
                )
        return redirect('pharmacy:s_add_medicine')
                 
    return render(request,'pharmacy/s-add-medicine.html')

@login_required
def delete_medicine(request):
    
    search = request.GET.get('search', '')

    if search:
        medicines = Medicine.objects.filter(name__icontains=search)
    else:
        medicines = Medicine.objects.all()

    return render(request, 'pharmacy/delete-medicine.html', {
        'medicines': medicines,
        'search': search,
    })

@login_required
def delete_med(request,pk):
    if request.method == 'POST':
        medicine = get_object_or_404(Medicine, pk=pk)
        medicine.delete()
    return redirect('pharmacy:delete_medicine')

@login_required
def add_salesman(request):

    if request.method == 'POST':
        salesman_name = request.POST.get('salesman_name', '').strip()
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '').strip()

        # Check if username already exists
        if User.objects.filter(username=username).exists():
            salesmen = User.objects.filter(is_superuser=False, is_active=True)
            return render(request, 'pharmacy/add-salesman.html', {
                'salesmen': salesmen,
                'error': f"Username '{username}' already exists. Choose a different one.",
            })

        # Create the salesman as a regular Django user
        user = User.objects.create_user(
            username=username,
            password=password,
            first_name=salesman_name,
            is_staff=False,
            is_superuser=False,
        )

        salesmen = User.objects.filter(is_superuser=False, is_active=True)
        return render(request, 'pharmacy/add-salesman.html', {
            'salesmen': salesmen,
            'success': f"Salesman '{salesman_name}' added successfully!",
        })

    salesmen = User.objects.filter(is_superuser=False, is_active=True)
    return render(request, 'pharmacy/add-salesman.html', {
        'salesmen': salesmen,
    })


@login_required
def delete_salesman(request, pk):
    if request.method == 'POST':
        user = get_object_or_404(User, pk=pk)
        user.delete()
    return redirect('pharmacy:add_salesman')

@login_required
def sale_medicines(request):
    if request.method == 'POST':
        total_count = int(request.POST.get('total_count',0))
        discount = float(request.POST.get('discount', 0))
        subtotal = float(request.POST.get('subtotal',0))
        final_price = float(request.POST.get('final_price',0))
        errors = []

        for i in range(total_count):
            name =  request.POST.get(f'sale_{i}_name')
            quantity   = int(request.POST.get(f'sale_{i}_quantity', 0))
            price      = float(request.POST.get(f'sale_{i}_price', 0))
            item_total = float(request.POST.get(f'sale_{i}_total', 0))

            try:
                medicine = Medicine.objects.get(name__iexact=name)
            except:
                errors.append(f"Medicine '{name}' not found.")
                continue

            if medicine.quantity<quantity:
                errors.append(
                    f"Not enough stock for '{name}.'"
                    f"Available: {medicine.quantity}, Requested: {quantity}"
                )
                continue

            Sale.objects.create(
                    medicine=medicine,
                    salesman=request.user,
                    quantity_sold=quantity,
                    price_per_unit=price,
                    item_total=item_total,
                    subtotal=subtotal,
                    discount=discount,
                    final_price=final_price,
            )

            medicine.quantity -= quantity
            medicine.save()


        if errors:
            return render(request,'pharmacy/sale-medicine.html',{'errors':errors})

        return redirect('pharmacy:sale_medicines')
        
    return render(request,'pharmacy/sale-medicine.html')

from django.http import JsonResponse

@login_required
def get_medicine_price(request):
    name = request.GET.get('name', '').strip()
    try:
        medicine = Medicine.objects.get(name__iexact=name)
        return JsonResponse({
            'found': True,
            'price': float(medicine.price_per_unit),
            'stock': medicine.quantity,
            'product_type': medicine.product_type,
        })
    except Medicine.DoesNotExist:
        return JsonResponse({'found': False})

@login_required
def wholesale(request):
    if request.method == 'POST':
        buyer_name = request.POST.get('buyer_name','').strip()
        total_count = int(request.POST.get('total_count',0))
        discount = float(request.POST.get('discount',0))
        subtotal = float(request.POST.get('subtotal',0))
        final_price = float(request.POST.get('final_price',0))
        errors = []

        # Buyer name is required
        if not buyer_name:
            return render(request,'pharmacy/wholesale.html',{'errors': ['Buyer name is required']})

        for i in range(total_count):
            name = request.POST.get(f'sale_{i}_name')
            quantity = request.POST.get(f'sale_{i}_quantity')
            price = request.POST.get(f'sale_{i}_price')
            item_total = request.POST.get(f'sale_{i}_total')

            if not name or quantity or not price:
                continue

            quantity = int(quantity)
            price = float(price)
            item_total = float(item_total)

            try:
                medicine = Medicine.objects.get(name__iexact=name)
            except Medicine.DoesNotExist:
                errors.append(f"Medicine '{name}' not found.")
                continue

            if medicine.quantity<quantity:
                errors.append(
                    f"Not enough stock for '{name}.'"
                    f"Available: {medicine.quantity}, Requested: {quantity}"
                )
                continue
            Wholesale.objects.create(
                buyer_name = buyer_name,
                medicine=medicine,
                salesman=request.user,
                quantity_sold=quantity,
                price_per_unit=price,
                item_total=item_total,
                subtotal=subtotal,
                discount=discount,
                final_price=final_price,
            )
            
            medicine.quantity -= quantity
            medicine.save()

        if errors:
            return render(request,'pharamacy/wholesale.html', {'errors': errors})

        return redirect('pharmacy:wholesale')

    return render(request,'pharmacy/wholesale.html')


@login_required
def get_wholesale_price(request):
    name = request.GET.get('name', '').strip()
    try:
        medicine = Medicine.objects.get(name__iexact=name)
        return JsonResponse({
            'found': True,
            'price': float(medicine.price_per_unit),
            'stock': medicine.quantity,
            'product_type': medicine.product_type,
        })
    except Medicine.DoesNotExist:
        return JsonResponse({'found': False})
    
@login_required
def update_medicine(request):
    if request.method == 'POST':
            total_count = int(request.POST.get('total_count',0))
    
            for i in range(total_count):
                name = request.POST.get(f'medicine_{i}_name')
                company = request.POST.get(f'medicine_{i}_company')
                type_ = request.POST.get(f'medicine_{i}_type')
                quantity = request.POST.get(f'medicine_{i}_quantity')
                price = request.POST.get(f'medicine_{i}_price')
                total_price = request.POST.get(f'medicine_{i}_total_price')
    
                if name and type_ and quantity and price:
                     Medicine.objects.create(
                        name=name,
                        company=company, 
                        product_type=type_,
                        quantity=int(quantity),
                        price_per_unit=float(price),
                        total_price =float(total_price)
                    )
            return redirect('pharmacy:update_medicine')
                     
    return render(request,'pharmacy/update-medicine.html')

@login_required
def medicine_list(request):
    search = request.GET.get('search','').strip()
    company = request.GET.get('company','').strip()

    medicines = Medicine.objects.all()

    if search:
        medicines = medicines.filter(name__icontains=search)

    if company:
        medicines = medicines.filter(company__iexact=company)

    # Get unique company names for the dropdown filter
    companies = Medicine.objects.values_list(
        'company', flat=True
    ).distinct().order_by('company')

    return render(request, 'pharmacy/medicine-list.html', {
        'medicines': medicines,
        'companies': companies,
        'search': search,
        'selected_company': company,
    })

@login_required
def medicine_suggestions(request):
    query = request.GET.get('q', '').strip()
    suggestions = []

    if query:
        matches = Medicine.objects.filter(
            name__icontains=query
        ).values_list('name', flat=True).distinct()[:8]
        suggestions = list(matches)

    return JsonResponse({'suggestions': suggestions})

@login_required
def sales_report(request):
    tab  = request.GET.get('tab','today')
    today = timezone.localdate()

    sales_data = None
    wholesale_data = None
    purchase_data = None
    weekly_data  = None
    monthly_data = None
    yearly_data = None

    sale_total_today      = 0
    wholesale_total_today = 0
    purchase_total_today  = 0

    if tab == 'today':
        sales_data = Sale.objects.filter(sold_at__date=today).select_related('medicine','salesman').order_by('sold_at')
        wholesale_data = Wholesale.objects.filter(sold_at__date=today).select_related('medicine','salesman').order_by('sold_at')
        purchase_data = Purchase.objects.filter(purchased_at__date=today).select_related('medicine','added_by').order_by('purchased_at')

        sale_total_today = float(sales_data.aggregate(t=Sum('final_price'))['t'] or 0)
        wholesale_total_today = float(wholesale_data.aggregate(t=Sum('final_price'))['t'] or 0)
        purchase_total_today = float(purchase_data.aggregate(t=Sum('total_cost'))['t'] or 0)

    elif tab == 'weekly':
        # Find most recent Saturday
        # Python weekday(): Mon=0 Tue=1 Wed=2 Thu=3 Fri=4 Sat=5 Sun=6
        days_since_saturday = (today.weekday()-5)%7
        week_start = today - timedelta(days=days_since_saturday)

        day_names = [
            'Saturday', 'Sunday', 'Monday',
            'Tuesday', 'Wednesday', 'Thursday', 'Friday'
        ]

        weekly_data = []
        for i in range(7):
            day = week_start+ timedelta(days=i)

            day_sales = Sale.objects.filter(sold_at__date=day).aggregate(amount=Sum('final_price'),qty=Sum('quantity_sold'))
            day_wholesale = Wholesale.objects.filter(sold_at__date=day).aggregate(amount=Sum('final_price'),qty=Sum('quantity_sold'))
            day_purchases = Purchase.objects.filter(purchased_at__date=day).aggregate(amount=Sum('total_cost'),qty=Sum('quantity'))

            sale_amt = float(day_sales['amount'] or 0)
            wholesale_amt = float(day_wholesale['amount'] or 0)
            purchase_amt = float(day_purchases['amount'] or 0)

            weekly_data.append({
                'day_name':         day_names[i],
                'label':            day_names[i],
                'date':             day,
                'sale_qty':         day_sales['qty'] or 0,
                'sale_amount':      sale_amt,
                'wholesale_qty':    day_wholesale['qty'] or 0,
                'wholesale_amount': wholesale_amt,
                'purchase_qty':     day_purchases['qty'] or 0,
                'purchase_amount':  purchase_amt,
                'net':              (sale_amt + wholesale_amt) - purchase_amt,
                'is_today':         day == today,
            })

    elif tab == 'monthly':
        days_in_month = calendar.monthrange(today.year,today.month)[1]
        monthly_data = []
        for day_num in range(1,days_in_month+1):
            day = date(today.year,today.month,day_num)

            day_sales = Sale.objects.filter(sold_at__date=day).aggregate(amount=Sum('final_price'),
                                                                                     qty=Sum('quantity_sold'))
            day_wholesale = Wholesale.objects.filter(sold_at__date=day).aggregate(amount=Sum('final_price'),
                                                                                     qty=Sum('quantity_sold'))
            day_purchases = Purchase.objects.filter(purchased_at__date=day).aggregate(amount=Sum('total_cost'),
                                                                                     qty=Sum('quantity'))

            sale_amt = float(day_sales['amount'] or 0)
            wholesale_amt = float(day_wholesale['amount'] or 0)
            purchase_amt = float(day_purchases['amount'] or 0)

            monthly_data.append({
                'label':            day.strftime('%d %b'),
                'date':             day,
                'sale_qty':         day_sales['qty'] or 0,
                'sale_amount':      sale_amt,
                'wholesale_qty':    day_wholesale['qty'] or 0,
                'wholesale_amount': wholesale_amt,
                'purchase_qty':     day_purchases['qty'] or 0,
                'purchase_amount':  purchase_amt,
                'net':              (sale_amt + wholesale_amt) - purchase_amt,
                'is_today':         day == today,
            })

    elif tab == 'yearly':
        month_names = [
            'January', 'February', 'March', 'April',
            'May', 'June', 'July', 'August',
            'September', 'October', 'November', 'December'
        ]
        yearly_data=[]

        for month_num in range(1,13):
            month_sales = Sale.objects.filter(sold_at__year=today.year,sold_at__month=month_num ).aggregate(amount=Sum('final_price'),
                                                                                                 qty=Sum('quantity_sold'))
            month_wholesale = Wholesale.objects.filter(sold_at__year=today.year,sold_at__month=month_num).aggregate(amount=Sum('final_price'),
                                                                                                         qty=Sum('quantity_sold'))
            month_purchases = Purchase.objects.filter(purchased_at__year=today.year,purchased_at__month=month_num).aggregate(amount=Sum('total_cost'),
                                                                                                                    qty=Sum('quantity'))

            sale_amt = float(month_sales['amount'] or 0)
            wholesale_amt = float(month_wholesale['amount'] or 0)
            purchase_amt = float(month_purchases['amount'] or 0)

            yearly_data.append({
                'label':            month_names[month_num - 1],
                'sale_qty':         month_sales['qty'] or 0,
                'sale_amount':      sale_amt,
                'wholesale_qty':    month_wholesale['qty'] or 0,
                'wholesale_amount': wholesale_amt,
                'purchase_qty':     month_purchases['qty'] or 0,
                'purchase_amount':  purchase_amt,
                'net':              (sale_amt + wholesale_amt) - purchase_amt,
                'is_curernt':        month_num == today.month,
            })

    context = {
        'tab':                    tab,
        'today':                  today,
        'sales_data':             sales_data,
        'wholesale_data':         wholesale_data,
        'purchase_data':          purchase_data,
        'weekly_data':            weekly_data,
        'monthly_data':           monthly_data,
        'yearly_data':            yearly_data,
        'sale_total_today':       sale_total_today,
        'wholesale_total_today':  wholesale_total_today,
        'purchase_total_today':   purchase_total_today,
    }
    return render(request,'pharmacy/sales-report.html',context)