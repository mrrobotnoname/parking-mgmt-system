from pydantic import BaseModel
from fastapi import FastAPI,Depends
from app.db.session import init_db,get_session
from app.models.user import User
from app.routers.v1 import auth,admin
from app.core.security import encryptPassword

app = FastAPI()



@app.on_event("startup")
def on_startup():
    init_db()


@app.get("/")
def root():
    return "Bingo"


##This is only in the development please remove this class and the /adminreg in the producntoin Critical 10.0
class Admin(BaseModel):
    username:str
    password:str
    name:str
    phone_no:str
    role:str


@app.post("/adminreg")
async def admin_reg(user:Admin,db=Depends(get_session)):
    admin = User(username=user.username,password=encryptPassword(user.password),name=user.name,phone_number=user.phone_no,role=user.role)
    db.add(admin)
    db.commit()
    return "admin added"
    
app.include_router(auth.router,prefix="/api/v1/auth")
app.include_router(admin.router)


    