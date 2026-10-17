import json, sqlite3, os, re, hashlib, secrets, datetime
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from pathlib import Path
ROOT=Path(__file__).parent; DB=Path(os.environ.get('DB_PATH',str(ROOT/'science.db')))
DB.parent.mkdir(parents=True,exist_ok=True)
LESSONS=[(6,'Hóa học','Chất tinh khiết và hỗn hợp','Phân biệt chất tinh khiết, hỗn hợp và cách tách chất.'),(6,'Vật lí','Đo chiều dài và khối lượng','Thực hành đo và đọc kết quả.'),(6,'Sinh học','Tế bào','Cấu tạo và chức năng tế bào.'),(7,'Hóa học','Nguyên tử và nguyên tố','Nguyên tử, nguyên tố và kí hiệu hóa học.'),(7,'Vật lí','Tốc độ chuyển động','Vận dụng v=s/t.'),(7,'Sinh học','Quang hợp','Điều kiện và sản phẩm của quang hợp.'),(8,'Hóa học','Dung dịch và nồng độ','Khối lượng dung dịch và nồng độ phần trăm.'),(8,'Hóa học','Mol và khối lượng mol','n=m/M và các phép đổi.'),(8,'Hóa học','Phương trình hóa học','Định luật bảo toàn nguyên tử và cân bằng.'),(8,'Vật lí','Mạch điện','Hiệu điện thế và cường độ dòng điện.'),(8,'Sinh học','Hệ tuần hoàn','Tim và các mạch máu.'),(9,'Hóa học','Kim loại và dãy hoạt động','Phản ứng và tính chất của kim loại.'),(9,'Hóa học','Hydrocarbon','Methane, ethylene và nhiên liệu.'),(9,'Vật lí','Định luật Ohm','I=U/R và ứng dụng.'),(9,'Sinh học','Di truyền','Gene và đặc điểm di truyền.')]
QUESTIONS=[(8,'Hóa học','Dung dịch và nồng độ','Hòa tan 10 g NaCl vào 190 g nước. Nồng độ phần trăm của dung dịch là bao nhiêu?','5','Nồng độ phần trăm bằng khối lượng chất tan chia khối lượng dung dịch (200 g), nhân 100.','concentration'),(8,'Hóa học','Mol và khối lượng mol','Có 18 g nước (M = 18 g/mol). Số mol nước là bao nhiêu?','1','n = m/M = 18/18 = 1 mol.','mol'),(7,'Hóa học','Nguyên tử và nguyên tố','Kí hiệu hóa học của oxygen là gì?','O','Kí hiệu nguyên tố oxygen là O, phân tử oxygen thường là O₂.','symbol'),(9,'Hóa học','Kim loại và dãy hoạt động','Kim loại nào phản ứng với dung dịch HCl loãng: Cu hay Zn?','Zn','Zn đứng trước H trong dãy hoạt động; Cu không phản ứng với HCl loãng.','metals'),(6,'Hóa học','Chất tinh khiết và hỗn hợp','Nước muối là chất tinh khiết hay hỗn hợp?','hỗn hợp','Nước muối chứa nước và muối hòa tan.','mixture')]
def db():
 c=sqlite3.connect(DB); c.row_factory=sqlite3.Row; return c
def init():
 with db() as c:
  c.executescript('''CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY, username TEXT UNIQUE, password TEXT, salt TEXT, role TEXT, display_name TEXT);CREATE TABLE IF NOT EXISTS sessions(token TEXT PRIMARY KEY,user_id INTEGER);CREATE TABLE IF NOT EXISTS lessons(id INTEGER PRIMARY KEY,grade INTEGER,subject TEXT,title TEXT,description TEXT);CREATE TABLE IF NOT EXISTS questions(id INTEGER PRIMARY KEY,grade INTEGER,subject TEXT,topic TEXT,question TEXT,answer TEXT,explanation TEXT,skill TEXT);CREATE TABLE IF NOT EXISTS attempts(id INTEGER PRIMARY KEY,user_id INTEGER,question_id INTEGER,response TEXT,correct INTEGER,feedback TEXT,created_at TEXT);CREATE TABLE IF NOT EXISTS labs(id INTEGER PRIMARY KEY,user_id INTEGER,salt REAL,water REAL,prediction TEXT,correct INTEGER,created_at TEXT);''')
  if not c.execute('SELECT count(*) FROM lessons').fetchone()[0]: c.executemany('INSERT INTO lessons(grade,subject,title,description) VALUES(?,?,?,?)',LESSONS)
  if not c.execute('SELECT count(*) FROM questions').fetchone()[0]: c.executemany('INSERT INTO questions(grade,subject,topic,question,answer,explanation,skill) VALUES(?,?,?,?,?,?,?)',QUESTIONS)
  if os.environ.get('ENABLE_DEMO_ACCOUNTS','0') != '1': return
  for username,pw,role,name in [('giaovien','Teacher123!','teacher','Giáo viên Demo'),('hocsinh','Student123!','student','Học sinh Demo')]:
   if not c.execute('SELECT 1 FROM users WHERE username=?',(username,)).fetchone():
    salt=secrets.token_hex(16); digest=hashlib.pbkdf2_hmac('sha256',pw.encode(),bytes.fromhex(salt),200000).hex()
    c.execute('INSERT INTO users(username,password,salt,role,display_name) VALUES(?,?,?,?,?)',(username,digest,salt,role,name))
def normalize(s): return re.sub(r'\s+','',str(s).lower().replace(',','.')).replace('₂','2').replace('₃','3')
def grade_answer(q,ans):
 a=normalize(ans); expected=normalize(q['answer']); skill=q['skill']
 if skill in ('concentration','mol'):
  m=re.findall(r'(?<![\d])\d+(?:\.\d+)?',a)
  ok=bool(m) and abs(float(m[-1])-float(expected))<0.015
  if skill=='concentration' and ('10/190' in a or '10:190' in a or '5.26' in a): return False,'Nhầm khối lượng dung môi với khối lượng dung dịch. Hãy cộng khối lượng muối và nước trước khi tính.'
  if ok:return True,'Đúng! '+q['explanation']
  return False,'Chưa đúng. Gợi ý: '+('m dung dịch = m chất tan + m dung môi.' if skill=='concentration' else 'n = m/M.')
 ok=(a==expected or (skill=='mixture' and a in ('honhop','hỗnhợp')))
 return ok, ('Chính xác! ' if ok else 'Chưa chính xác. ')+q['explanation']
def parse_formula(formula):
 # supports basic formulas with parentheses, excludes ions and hydrates
 tokens=re.findall(r'[A-Z][a-z]?|\d+|[()]',formula)
 if ''.join(tokens)!=formula or not tokens: raise ValueError('Công thức không hợp lệ hoặc chưa được hỗ trợ')
 stack=[{}]; i=0
 while i<len(tokens):
  t=tokens[i]
  if t=='(':stack.append({});i+=1
  elif t==')':
   if len(stack)==1:raise ValueError('Ngoặc không cân')
   group=stack.pop();i+=1;mul=int(tokens[i]) if i<len(tokens) and tokens[i].isdigit() else 1
   if i<len(tokens) and tokens[i].isdigit():i+=1
   for k,v in group.items():stack[-1][k]=stack[-1].get(k,0)+v*mul
  elif re.match(r'[A-Z]',t):
   i+=1;mul=int(tokens[i]) if i<len(tokens) and tokens[i].isdigit() else 1
   if i<len(tokens) and tokens[i].isdigit():i+=1
   stack[-1][t]=stack[-1].get(t,0)+mul
  else:raise ValueError('Chỉ số không đúng vị trí')
 if len(stack)!=1:raise ValueError('Ngoặc không cân')
 return stack[0]
def side_counts(side):
 counts={}
 for part in side.split('+'):
  part=part.strip(); m=re.fullmatch(r'(\d*)\s*([A-Z][A-Za-z0-9()]*)',part)
  if not m:raise ValueError('Nhập phương trình dạng: 4Fe + 3O2 -> 2Fe2O3')
  coef=int(m.group(1) or 1)
  if coef<1:raise ValueError('Hệ số phải dương')
  for k,v in parse_formula(m.group(2)).items():counts[k]=counts.get(k,0)+coef*v
 return counts
def check_equation(e):
 pieces=re.split(r'\s*(?:->|→|=)\s*',e)
 if len(pieces)!=2:raise ValueError('Cần có mũi tên -> giữa hai vế')
 left=side_counts(pieces[0]);right=side_counts(pieces[1]); keys=sorted(set(left)|set(right))
 return {'balanced':all(left.get(k,0)==right.get(k,0) for k in keys),'atoms':[{'element':k,'left':left.get(k,0),'right':right.get(k,0)} for k in keys],'note':'Chỉ kiểm tra bảo toàn nguyên tử; không xác nhận phản ứng có xảy ra hay không.'}
class Handler(SimpleHTTPRequestHandler):
 def __init__(self,*a,**kw):super().__init__(*a,directory=str(ROOT/'static'),**kw)
 def send_json(self,data,status=200):
  raw=json.dumps(data,ensure_ascii=False).encode();self.send_response(status);self.send_header('Content-Type','application/json; charset=utf-8');self.send_header('Content-Length',str(len(raw)));self.send_header('Cache-Control','no-store');self.end_headers();self.wfile.write(raw)
 def body(self):
  n=int(self.headers.get('Content-Length','0'))
  if n>30000:raise ValueError('Dữ liệu quá lớn')
  return json.loads(self.rfile.read(n) or b'{}')
 def user(self):
  tok=self.headers.get('Authorization','').removeprefix('Bearer ').strip()
  with db() as c:return c.execute('SELECT users.id,users.role,users.display_name FROM users JOIN sessions ON users.id=sessions.user_id WHERE sessions.token=?',(tok,)).fetchone()
 def do_GET(self):
  path=urlparse(self.path).path
  if path=='/health':return self.send_json({'status':'ok'})
  if not path.startswith('/api/'):return super().do_GET()
  u=self.user()
  if not u:return self.send_json({'error':'Vui lòng đăng nhập'},401)
  with db() as c:
   if path=='/api/me':return self.send_json(dict(u))
   if path=='/api/lessons':return self.send_json([dict(x) for x in c.execute('SELECT * FROM lessons ORDER BY grade,subject,id')])
   if path=='/api/questions':return self.send_json([dict(x) for x in c.execute('SELECT id,grade,subject,topic,question,skill FROM questions')])
   if path=='/api/progress':
    rows=c.execute('SELECT q.topic,count(*) attempts,sum(a.correct) correct FROM attempts a JOIN questions q ON q.id=a.question_id WHERE a.user_id=? GROUP BY q.topic',(u['id'],)).fetchall()
    return self.send_json([dict(x) for x in rows])
   if path=='/api/dashboard':
    if u['role']!='teacher':return self.send_json({'error':'Không có quyền'},403)
    rows=c.execute('SELECT users.display_name,q.topic,count(*) attempts,sum(a.correct) correct FROM attempts a JOIN users ON a.user_id=users.id JOIN questions q ON q.id=a.question_id GROUP BY users.id,q.topic').fetchall()
    return self.send_json({'students':c.execute("SELECT count(*) FROM users WHERE role='student'").fetchone()[0],'attempts':c.execute('SELECT count(*) FROM attempts').fetchone()[0],'results':[dict(x) for x in rows]})
  return self.send_json({'error':'Không tìm thấy'},404)
 def do_POST(self):
  path=urlparse(self.path).path
  try:data=self.body()
  except Exception as e:return self.send_json({'error':str(e)},400)
  if path=='/api/login':
   with db() as c:
    row=c.execute('SELECT * FROM users WHERE username=?',(data.get('username'),)).fetchone()
    if not row:return self.send_json({'error':'Sai tài khoản hoặc mật khẩu'},401)
    digest=hashlib.pbkdf2_hmac('sha256',str(data.get('password','')).encode(),bytes.fromhex(row['salt']),200000).hex()
    if not secrets.compare_digest(digest,row['password']):return self.send_json({'error':'Sai tài khoản hoặc mật khẩu'},401)
    tok=secrets.token_urlsafe(32);c.execute('INSERT INTO sessions VALUES(?,?)',(tok,row['id']))
    return self.send_json({'token':tok,'role':row['role'],'display_name':row['display_name']})
  u=self.user()
  if not u:return self.send_json({'error':'Vui lòng đăng nhập'},401)
  if path=='/api/logout':
   tok=self.headers.get('Authorization','').removeprefix('Bearer ').strip()
   with db() as c:c.execute('DELETE FROM sessions WHERE token=?',(tok,))
   return self.send_json({'ok':True})
  if path=='/api/equation':
   try:return self.send_json(check_equation(str(data.get('equation',''))))
   except ValueError as e:return self.send_json({'error':str(e)},400)
  if path=='/api/attempt':
   with db() as c:
    q=c.execute('SELECT * FROM questions WHERE id=?',(data.get('question_id'),)).fetchone()
    if not q:return self.send_json({'error':'Câu hỏi không tồn tại'},404)
    ans=str(data.get('response',''))[:3000];ok,feedback=grade_answer(q,ans)
    c.execute('INSERT INTO attempts(user_id,question_id,response,correct,feedback,created_at) VALUES(?,?,?,?,?,?)',(u['id'],q['id'],ans,int(ok),feedback,datetime.datetime.now(datetime.timezone.utc).isoformat()))
    return self.send_json({'correct':ok,'feedback':feedback,'answer':q['answer']})
  if path=='/api/lab':
   try:
    salt=float(data['salt']);water=float(data['water']);prediction=data['prediction']
    if not 0<=salt<=200 or not 10<=water<=500 or prediction not in ('all','remain'):raise ValueError()
   except (ValueError,KeyError,TypeError):return self.send_json({'error':'Thông số không hợp lệ'},400)
   maxsol=water*.36;dissolved=min(salt,maxsol);remaining=max(0,salt-maxsol);correct=(prediction=='all')==(remaining<1e-8)
   with db() as c:c.execute('INSERT INTO labs(user_id,salt,water,prediction,correct,created_at) VALUES(?,?,?,?,?,?)',(u['id'],salt,water,prediction,int(correct),datetime.datetime.now(datetime.timezone.utc).isoformat()))
   return self.send_json({'max_soluble':round(maxsol,2),'dissolved':round(dissolved,2),'remaining':round(remaining,2),'correct':correct,'note':'Mô hình lý tưởng hóa: độ tan NaCl = 36 g/100 g nước ở điều kiện cố định.'})
  return self.send_json({'error':'Không tìm thấy'},404)
if __name__=='__main__':
 init();port=int(os.environ.get('PORT','8000'));host=os.environ.get('HOST','127.0.0.1');print(f'SCIENCE AI 360 listening on {host}:{port}',flush=True);ThreadingHTTPServer((host,port),Handler).serve_forever()
