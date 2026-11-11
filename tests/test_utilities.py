import unittest
from datetime import timedelta
import test_pickup
from biblioteca import data, db, circulation
from biblioteca.seed import seed_utilities_demo
from biblioteca.timeutils import local_input

class UtilitiesTests(unittest.TestCase):
    setUp = test_pickup.PickupTests.setUp
    tearDown = test_pickup.PickupTests.tearDown

    def client_for(self, user):
        client = self.app.test_client()
        with client.session_transaction() as session:
            session['user_id'] = user
            session['session_version'] = data.user(user)['session_version']
        return client

    def test_sections_search_and_seed_idempotence(self):
        seed_utilities_demo()
        seed_utilities_demo()
        self.assertEqual(len(data.books(resource_type='utility')), 7)
        client = self.client_for(self.student)
        books = client.get('/catalogo')
        utilities = client.get('/utilidades')
        self.assertEqual(utilities.status_code, 200)
        self.assertNotIn('Laptop para estudio', books.text)
        self.assertIn('Laptop para estudio', utilities.text)
        self.assertNotIn('>Prueba</a>', utilities.text)
        filtered = client.get('/utilidades?category=Cargadores').text
        self.assertIn('Cargador USB-C', filtered)
        self.assertNotIn('Laptop para estudio', filtered)
        self.assertIn('Agregar a favoritos', utilities.text)

    def test_admin_create_edit_and_student_cannot_create(self):
        client = self.client_for(self.admin)
        form = dict(title='Notebook de prueba',author='',category='Laptops',publication_year='',isbn='',description='Demo')
        self.assertEqual(client.get('/admin/libros/nuevo?type=utility').status_code,200)
        result = client.post('/admin/libros/nuevo?type=utility',data=form)
        self.assertEqual(result.status_code,302)
        resource = data.books(resource_type='utility')[0]
        self.assertEqual(resource['title'], form['title'])
        self.assertEqual(client.get(result.location).status_code,200)
        form['title']='Notebook actualizado'
        self.assertEqual(client.post(f"/admin/libros/{resource['id']}/editar", data=form).status_code,302)
        self.assertEqual(data.book(resource['id'])['resource_type'],'utility')
        self.assertEqual(self.client_for(self.student).post('/admin/libros/nuevo?type=utility',data=form).status_code,403)

    def test_utility_inventory_and_favorites(self):
        seed_utilities_demo()
        item=data.books(category='Laptops',resource_type='utility')[0]
        copy=data.copies(item['id'])[0]
        req=circulation.submit(self.student,item['id'],'general',2)
        circulation.approve(self.admin,req,copy['id'])
        self.assertEqual(data.books(category='Laptops',resource_type='utility')[0]['available'],1)
        circulation.mark_ready(self.admin,req)
        circulation.deliver(self.admin,req,local_input(self.now+timedelta(days=2)),True)
        self.assertEqual(data.copy(copy['id'])['state'],'prestado')
        client=self.client_for(self.student)
        result=client.post(f"/libros/{item['id']}/favorito",data={'action':'add','return_to':'utilities'})
        self.assertTrue(result.location.endswith('/utilidades'))
        self.assertIn('Laptop para estudio',client.get('/favoritos').text)

    def test_favorite_json_updates_without_redirect_or_flash(self):
        client = self.client_for(self.student)
        for action, expected in [('add', True), ('remove', False)]:
            response = client.post(f'/libros/{self.book}/favorito',
                data={'action': action}, headers={'Accept': 'application/json'})
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json['favorite'], expected)
            self.assertEqual(self.book in data.favorite_ids(self.student), expected)
            with client.session_transaction() as session:
                self.assertNotIn('_flashes', session)
