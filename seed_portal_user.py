from app import app, db
from models import Client, ClientUser


def main():
    email = "client@example.com"
    password = "client123"
    first_name = "Demo"
    last_name = "Client"

    with app.app_context():
        # Ensure client exists
        client = Client.query.filter(db.func.lower(Client.email) == email.lower()).first()
        if not client:
            client = Client(first_name=first_name, last_name=last_name, email=email)
            db.session.add(client)
            db.session.flush()  # assign client.id

        # Ensure portal user exists
        cu = ClientUser.query.filter(db.func.lower(ClientUser.email) == email.lower()).first()
        if not cu:
            cu = ClientUser(client_id=client.id, email=email)
            cu.set_password(password)
            db.session.add(cu)
            created = True
        else:
            cu.set_password(password)
            created = False

        db.session.commit()
        action = "Created" if created else "Updated"
        print(f"{action} portal user:")
        print(f"  Email: {email}")
        print(f"  Password: {password}")
        print(f"  Client ID: {client.id}")
        print(f"  ClientUser ID: {cu.id}")


if __name__ == "__main__":
    main()