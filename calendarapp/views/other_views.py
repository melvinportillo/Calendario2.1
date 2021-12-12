# cal/views.py

from django.shortcuts import render, redirect
from django.http import HttpResponseRedirect
from django.views import generic
from django.utils.safestring import mark_safe
from datetime import timedelta, datetime, date
import calendar
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy, reverse
import pandas as pd
from accounts.models import  user
from calendarapp.models import EventMember, Event
from calendarapp.models.linea_presupuesto import Cronogram, Line_Presupuesto
from calendarapp.utils import Calendar
from calendarapp.forms import EventForm, AddMemberForm, excel_form
from django.utils.functional import SimpleLazyObject
from django.contrib import messages

def get_date(req_day):
    if req_day:
        year, month = (int(x) for x in req_day.split('-'))
        return date(year, month, day=1)
    return datetime.today()


def prev_month(d):
    first = d.replace(day=1)
    prev_month = first - timedelta(days=1)
    month = 'month=' + str(prev_month.year) + '-' + str(prev_month.month)
    return month


def next_month(d):
    days_in_month = calendar.monthrange(d.year, d.month)[1]
    last = d.replace(day=days_in_month)
    next_month = last + timedelta(days=1)
    month = 'month=' + str(next_month.year) + '-' + str(next_month.month)
    return month


class CalendarView(LoginRequiredMixin, generic.ListView):
    login_url = 'accounts:signin'
    model = Event
    template_name = 'calendar.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        d = get_date(self.request.GET.get('month', None))
        cal = Calendar(d.year, d.month)
        html_cal = cal.formatmonth(withyear=True)
        context['calendar'] = mark_safe(html_cal)
        context['prev_month'] = prev_month(d)
        context['next_month'] = next_month(d)
        return context


@login_required(login_url='signup')
def create_event(request):
    form = EventForm(request.POST or None)
    if request.POST and form.is_valid():
        title = form.cleaned_data['title']
        description = form.cleaned_data['description']
        start_time = form.cleaned_data['start_time']
        end_time = form.cleaned_data['end_time']
        Event.objects.get_or_create(
            user=request.user,
            title=title,
            description=description,
            start_time=start_time,
            end_time=end_time
        )
        return HttpResponseRedirect(reverse('calendarapp:calendar'))
    return render(request, 'event.html', {'form': form})


class EventEdit(generic.UpdateView):
    model = Event
    fields = ['title', 'description', 'start_time', 'end_time','Presupuesto']
    template_name = 'event.html'


@login_required(login_url='signup')
def agregar_aprobacion(request, event_id):
    if  request.method=="GET":
         return render(request,'Aprobación.html')
    else:
        comentario = request.POST['Comentario']
        aprov = request.POST['Aprobacion']
        value_=True
        if aprov=='0':
            value_=False
        event = EventMember.objects.get(event_id=event_id,user=request.user)
        event.Comentario=comentario
        event.Aprobacion= value_
        event.save()
        link = "/event/"+str(event_id)+"/details/"
        return  redirect(link)


@login_required(login_url='signup')
def event_details(request, event_id):
    event = Event.objects.get(id=event_id)
    eventmember = EventMember.objects.filter(event=event)
    line_id = event.linea_p_id
    linia  = Line_Presupuesto.objects.get(Id=line_id)
    prespuesto = event.Presupuesto
    context = {
        'event': event,
        'eventmember': eventmember,
        'linea': linia,
        'presupuest': prespuesto,
    }
    proyecto = event.Proyecto
    Actualizar_Saldos(proyecto)
    return render(request, 'event-details.html', context)


def add_eventmember(request, event_id):
    forms = AddMemberForm()
    if request.method == 'POST':
        forms = AddMemberForm(request.POST)
        if forms.is_valid():
            member = EventMember.objects.filter(event=event_id)
            event = Event.objects.get(id=event_id)
            if member.count() <= 9:
                user = forms.cleaned_data['user']
                EventMember.objects.create(
                    event=event,
                    user=user
                )
                return redirect('calendarapp:calendar')
            else:
                print('--------------User limit exceed!-----------------')
    context = {
        'form': forms
    }
    return render(request, 'add_member.html', context)


class EventMemberDeleteView(generic.DeleteView):
    model = EventMember
    template_name = 'event_delete.html'
    success_url = reverse_lazy('calendarapp:calendar')


class CalendarViewNew(LoginRequiredMixin, generic.View):
    login_url = 'accounts:signin'
    template_name = 'calendarapp/calendar.html'
    form_class = EventForm

    def get(self, request, *args, **kwargs):
        forms = self.form_class()
        events = Event.objects.get_all_events(user=request.user)
        # Mostrar solo lineas de proyectos participates
        e_partica = Event.objects.filter(user=request.user)
        lineas=[]
        for even in e_partica:
            lina= even.linea_p_id
            if not lina in  lineas:
                lineas.append(lina)
        events_month=[]

        for line_id in lineas:
            Linea_p = Line_Presupuesto.objects.get(Id=line_id)
            events_month.append(Linea_p)

        #events_month = Line_Presupuesto.objects.all()
        event_list = []
        # start: '2020-09-16T16:00:00'
        for event in events:
            event_list.append({
                'title': event.title,
                'start': event.start_time.date().strftime("%Y-%m-%dT%H:%M:%S"),
                'end': event.end_time.date().strftime("%Y-%m-%dT%H:%M:%S"),
            })
        context = {
            'form': forms,
            'events': event_list,
            'events_month': events_month
        }
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        forms = self.form_class(request.POST)
        if forms.is_valid():
            form = forms.save(commit=False)
            form.user = request.user
            form.save()
            return redirect('calendarapp:calendar')
        context = {
            'form': forms
        }
        return render(request, self.template_name, context)


@login_required(login_url='signup')
def sub_excel(request):
    if request.method=='POST':
        form_1 = excel_form(request.POST, request.FILES)
        if form_1.is_valid():
            form_1.save()
        ultimo = Cronogram.objects.last()
        archivo = ultimo.Archivo_excel
        proyecto = ultimo.Proyecto
        user_list = list(user.User.objects.all())
        df = pd.ExcelFile(archivo)
        df1 = df.parse('Consolidado Nacional')
        df2 = df.parse('Presupuesto')

        total= Line_Presupuesto.objects.all().count()
        line_list = list(Line_Presupuesto.objects.all())
        o = [str(i) for i in line_list]


        for u in range (len(df2)):
            if (not (df2['Código'][u] in o)) and (type(df2['Código'][u]) == str):
                total+=1
                Line_Presupuesto.objects.get_or_create(
                    Id=total,
                    Codigo=str(df2['Código'][u]),
                    Total=df2['Presupuesto'][u],
                    Ejecutado=0,
                    En_Ejucucion=0,
                    Saldo=df2['Presupuesto'][u],
                    Proyecto=proyecto,
                )
        line_list1 = list(Line_Presupuesto.objects.all())
        o1 = [str(i) for i in line_list1]
        year = df1['Unnamed: 8'][4]
        year1 = year.split(': ')
        try:
            print(year1[1])
        except IndexError:
            mensaje=f'MENSAJE DE ERROR: Asegurese que en {year} haya un espacio antes del año'
            messages.error(request, mensaje)
            return render(request, 'subir_excel.html')

        actividad = 'sin actividad1'
        for i in range(9, len(df1)):
            act1 = actividad
            actividad = df1['Unnamed: 2'][i]
            if not type(actividad) == str:
                actividad = act1

            unidad_de_medida = df1['Unnamed: 3'][i]
            if not type(unidad_de_medida) == str:
                mensaje ="Error en la columna 'Unidad de medida' en la fila " + str(i+2)
                messages.error(request,mensaje)
                return render(request, 'subir_excel.html')


            cantidad = df1['Unnamed: 4'][i]
            if not type(cantidad) == int:
                mensaje = "Error en la columna 'Cantidad' en la fila " + str(i + 2)
                messages.error(request, mensaje)
                return render(request, 'subir_excel.html')


            encargado = df1['Unnamed: 5'][i]
            if not type(encargado) == str:
                mensaje = f"No asignó encargado a la actividad '{actividad}' en unidad de medida: '{unidad_de_medida}'"
                messages.error(request, mensaje)
                return render(request, 'subir_excel.html')

            responsables = df1['Unnamed: 6'][i]
            if not type(responsables) == str:
                mensaje = f"No asignó responsables a la actividad '{actividad}' en unidad de medida: '{unidad_de_medida}'"
                messages.error(request, mensaje)
                return render(request, 'subir_excel.html')


            lista_responsables = responsables.split(', ')
            lista_responsables.append(encargado)

            linea_presupuestaria = df1['Unnamed: 7'][i]



            if linea_presupuestaria in o1:
                lineap=Line_Presupuesto.objects.get(Codigo=linea_presupuestaria).Id
            else:
                mensaje = f"La linea presupuestaria '{linea_presupuestaria}' de la actividad '{actividad} no está definida"
                messages.error(request, mensaje)
                return render(request, 'subir_excel.html')


            if not type(responsables) == str:
                mensaje = f"No asignó linea presupuestaria a la actividad '{actividad}' en unidad de medida: '{linea_presupuestaria}'"
                messages.error(request, mensaje)
                return render(request, 'subir_excel.html')

            L=[str(r) for r in user_list]

            for j in lista_responsables:
                if not j in L:
                    mensaje = f'El usuario "{j}" asignado a la actividad "{actividad}" no existe'
                    messages.error(request, mensaje)
                    return render(request, 'subir_excel.html')

            lista_responsables.remove(encargado)

            mes = {}
            numero_months = []
            for j in range(12):
                m = 8 + 3 * j
                name = 'Unnamed:'
                name1 = ' '.join((name, str(m)))
                name2 = ' '.join((name, str(m + 1)))
                name3 = ' '.join((name, str(m + 2)))
                if (not df1[name1][i] == 0) and type(df1[name1][i])==int:
                    numero_months.append(j + 1)
                mes[df1[name1][7]] = {"P": df1[name1][i], "E": df1[name2][i], "T": df1[name3][i]}

            var=1
            for j in numero_months:
                title = f"{unidad_de_medida}({var})({year1[1]}): {actividad}"
                if j < 10:
                    month = '0' + str(j)
                else:
                    month = str(j)
                date_time_str0 = year1[1] + '-' + month + '-01 07'
                date_time_obj0 = datetime.strptime(date_time_str0, '%Y-%m-%d %H')
                date_time_str1 = year1[1] + '-' + month + '-28 20'
                date_time_obj1 = datetime.strptime(date_time_str1, '%Y-%m-%d %H')
                f= Event.objects.filter(title=title).count()
                if f==0:
                    for jj in user_list:
                        if encargado == str(jj):
                            c = Event.objects.get_or_create(
                                user=SimpleLazyObject(lambda: jj),
                                title=title,
                                description='Sin descripción',
                                start_time=date_time_obj0,
                                end_time=date_time_obj1,
                                linea_p_id=lineap,
                                Proyecto=proyecto,
                                Presupuesto=0.0,
                            )
                            var+=1
                            a=Event.objects.get(title=title).id
                            event = Event.objects.get(id=a)

                            for i in lista_responsables:
                                for j in user_list:
                                    if i == str(j):
                                        EventMember.objects.create(
                                            event=event,
                                            user=j,
                                            Comentario="Sin Comentario",
                                            Aprobacion=True
                                        )

        return HttpResponseRedirect(reverse('calendarapp:calendar'))
    else:
        ctx ={'form': excel_form}
        return  render(request,'subir_excel.html',ctx)

def Actualizar_Saldos(proyecto):
    cuentas = Line_Presupuesto.objects.filter(Proyecto=proyecto)
    for cuenta in cuentas:
        cuenta_id= cuenta.Id
        actividades_activas = Event.objects.filter(Proyecto=proyecto, is_deleted=False, linea_p_id=cuenta_id)
        total=0
        for actividad in actividades_activas:
            presupuesto = actividad.Presupuesto
            total=total+presupuesto
        cuenta.En_Ejucucion=total
        cuenta.Saldo=cuenta.Total-total
        cuenta.save()



