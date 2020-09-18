"""
MIT License

Copyright (c) 2020 Fyssion

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

import datetime

import sqlalchemy
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker


# Using an SQLite db for logging times
engine = sqlalchemy.create_engine("sqlite:///data/timedata.db")
Base = declarative_base()


class Program(Base):
    """Represents a program that timetracker will track"""

    __tablename__ = "programs"

    id = Column(Integer, primary_key=True)
    name = Column(String)
    process_name = Column(String)
    location = Column(String)
    time_entries = relationship(
        "TimeEntry", order_by="desc(TimeEntry.start_datetime)", lazy="dynamic"
    )
    added_at = Column(DateTime, default=datetime.datetime.utcnow)

    def __repr__(self):
        return f"<Program(name='{self.name}', process_name='{self.process_name}')>"


class TimeEntry(Base):
    """Represents an entry of time for a program"""

    __tablename__ = "time_entrys"

    id = Column(Integer, primary_key=True)
    program_id = Column(Integer, ForeignKey("programs.id"))
    program = relationship(Program, primaryjoin=program_id == Program.id)
    start_datetime = Column(DateTime)
    end_datetime = Column(DateTime)

    @staticmethod
    def start_logging(program_id):
        """Creates a time entry with the program id and the start time"""
        entry = TimeEntry(
            program_id=program_id, start_datetime=datetime.datetime.utcnow()
        )
        session.add(entry)
        session.commit()

    @staticmethod
    def stop_logging(program_id):
        """Updates a time entry with the end time"""
        entry = (
            session.query(TimeEntry)
            .filter_by(program_id=program_id, end_datetime=None)
            .order_by(TimeEntry.end_datetime.desc())
            .first()
        )
        entry.end_datetime = datetime.datetime.utcnow()
        session.commit()

    @staticmethod
    def delete_unfinished_entries():
        """Deletes all unfinished entries (entires without an end time)"""
        entries = (
            session.query(TimeEntry)
            .filter_by(end_datetime=None)
            .order_by(TimeEntry.end_datetime.desc())
        )

        for entry in entries:
            session.remove(entry)

        session.commit()


Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)
session = Session()
