from django.shortcuts import render,redirect
from django.contrib.auth import authenticate,login,logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .forms import LoginForm

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
        
        return render( request,"pharmacy/login.html",{"error": "Invalid username or password"})
        
    return render(request, 'pharmacy/login.html')

@login_required
def dashboard(request):
    if not request.user.is_authenticated:
        return redirect('pharmacy:login')
    return render(request,'pharmacy/index.html')

# Logout view
def logout_view(request):
    logout(request)
    return redirect('pharmacy:login') # redirct to login function

# Add Medicine
@login_required
def add_medicine(request):
    return render(request,'pharmacy/add-medicine.html')


