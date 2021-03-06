from ims.database import DatabaseConnection
from ims.exception import *
from sqlalchemy import Column, Integer, String
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import relationship


# This class is responsible for doing CRUD operations on the Project Table in DB
# This class was written as per the Repository Model which allows us to change the DB in the future without changing
# business code
class ProjectRepository:
    # inserts the arguments into the table
    # commits after insertion otherwise rollback occurs after which exception is bubbled up
    def insert(self, name, provision_network, id=None):
        with DatabaseConnection() as connection:
            try:
                p = Project()
                p.name = name
                p.provision_network = provision_network
                if id is not None:
                    p.id = id
                connection.session.add(p)
                connection.session.commit()
            except SQLAlchemyError as e:
                connection.session.rollback()
                raise db_exceptions.ORMException(e.message)

    # deletes project with name
    # commits after deletion otherwise rollback occurs after which exception is bubbled up
    def delete_with_name(self, name):
        with DatabaseConnection() as connection:
            try:
                project = connection.session.query(Project).filter_by(
                    name=name).one_or_none()
                if project is not None:
                    connection.session.delete(project)
                connection.session.commit()
            except SQLAlchemyError as e:
                connection.session.rollback()
                raise db_exceptions.ORMException(e.message)

    # fetch the project id with name
    # only project object is returned as the name is unique
    def fetch_id_with_name(self, name):
        with DatabaseConnection() as connection:
            try:
                project = connection.session.query(Project).filter_by(
                    name=name).one_or_none()
                if project is not None:
                    return project.id
            except SQLAlchemyError as e:
                raise db_exceptions.ORMException(e.message)


# This class represents the project table
# the Column variables are the columns in the table
# the relationship variable is loaded eagerly as the session is terminated after the object is retrieved
# The relationship is also delete on cascade
# images relationship is a reverse relation for easy traversal if required
class Project(DatabaseConnection.Base):
    __tablename__ = "project"

    # Columns in the table
    id = Column(Integer, primary_key=True, nullable=False, autoincrement=True)
    name = Column(String, nullable=False, unique=True)
    provision_network = Column(String, nullable=False)

    # Relationships in the table, this one back populates to project in Image Class, eagerly loaded
    # and cascade on delete is enabled
    images = relationship("Image", back_populates="project",
                          cascade="all, delete, delete-orphan")
