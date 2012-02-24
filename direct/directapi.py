import urllib2, urllib, json, time, hashlib
from google.appengine.ext import db

class YaCampany(db.Model):
	camp_id = db.StringProperty(required=True)
	amount = db.IntegerProperty(default=0)
	end_date = db.DateProperty()
	strategy = db.IntegerProperty(default=0)
	last_amount = db.IntegerProperty(default=0)
	last_invoice = db.IntegerProperty(default=0)
	last_rest = db.FloatProperty()

class YaCampanyLogs(db.Model):
	camp_id = db.ReferenceProperty(YaCampany)
	date = db.DateTimeProperty(auto_now=True)
	amount = db.IntegerProperty(default=0)
	plan = db.IntegerProperty(default=0)
	act = db.StringProperty()

class YaReport(db.Model):
	camp_id = db.ReferenceProperty(YaCampany)
	date = db.DateProperty()
	rtype = db.IntegerProperty(default=0)
	rep = db.TextProperty()
	shortrep = db.TextProperty()
	dicts = db.TextProperty()
	
class YaObject():
	def __init__(self,login,password,app_id,secret_id):
		data={'grant_type':'password','username':login,'password':password,'client_id':app_id,'client_secret':secret_id}
		response = urllib2.urlopen('https://oauth.yandex.ru/token',urllib.urlencode(data))
		self.token=json.loads(response.read().decode('utf8'))['access_token']
		self.login=login
		self.app_id=app_id

	def YaRequest(self,func,params,dop={}):
		data = {
		    'method': func,
		    'login': self.login,
		    'application_id': self.app_id,
		    'token': self.token,
		    'locale': 'ru',
		    'param': params
		}
		for key in dop:
			data[key]=dop[key]
		jdata = json.dumps(data, ensure_ascii=False).encode('utf8')
		response = urllib2.urlopen('https://soap.direct.yandex.ru/live/v4/json/', jdata)
		scamps = response.read().decode('utf8')
		res=json.loads(scamps)
		if 'data' not in res:
			return None
		else:
			return res['data']
	def createFinanceToken(self,oper_num):
		master_token="P3vwRqG1dGjef1Kg"
		method="CreateInvoice"
		login="luk-direct"	
		return hashlib.sha256(str(master_token)+str(oper_num)+str(method)+str(login)).hexdigest()
	def CreateInvoice(self,camp_id,sum,opnum):
		ftoken=self.createFinanceToken(opnum)
		arr=self.YaRequest('CreateInvoice',{'Payments': [{'CampaignID': int(camp_id), 'Sum': int(sum)}],'finance_token': ftoken,'operation_num': opnum},{'finance_token': ftoken,'operation_num': opnum})
		return arr
	def GetClientsList(self):
		arr=self.YaRequest('GetClientsList',{'Filter': {'StatusArch': 'No'}})
		logins=[]
		for key in arr:
		    logins.append(key['Login'])
		return logins
	def GetCampaignsList(self,logins):
		arr=self.YaRequest('GetCampaignsList',logins)
		camp_id={}
		for key in arr:
		    if key["StatusArchive"]=="No" and key["StatusModerate"]=="Yes":
			    camp_id[key["CampaignID"]]=key
		return camp_id
	def GetReportList(self,camp_id):
		arr=self.YaRequest('GetReportList',camp_id)
		out={}
		for itm in arr:
			out[itm["ReportID"]]=itm
		return out
	def DeleteReport(self,rep_id):
		arr=self.YaRequest('DeleteReport',rep_id)
		return arr
	def StopCampaign(self,camp_id):
		arr=self.YaRequest('StopCampaign',{"CampaignID" : camp_id})
		return arr
	def ResumeCampaign(self,camp_id):
		arr=self.YaRequest('ResumeCampaign',{"CampaignID" : camp_id})
		return arr
	def GetCampaignParams(self,camp_id):
		arr=self.YaRequest('GetCampaignParams',{"CampaignID" : camp_id})
		return arr
	def GetCampaignsParams(self,camp_ids):
		arr=self.YaRequest('GetCampaignsParams',{"CampaignIDS" : camp_ids})
		out={}
		if arr is not None:
			for key in arr:
				out[key["CampaignID"]]=key
		return out
	def CreateNewReport(self,camp_id,start_date,end_date,groupby=["clDate"]):
		arr=self.YaRequest('CreateNewReport',{"CampaignID":camp_id,"StartDate":start_date,"EndDate":end_date,"GroupByDate":"day","GroupByColumns":groupby,"Filter":{}})
		return arr
	def GetReport(self,camp_id,rep_id):
		reps=self.GetReportList(camp_id)		
		if rep_id in reps:
			while (rep_id in reps) and (reps[rep_id]["StatusReport"]=="Pending"):
				time.sleep(5)
				reps=self.GetReportList(camp_id)
			if rep_id in reps:
				response =urllib2.urlopen(reps[rep_id]["Url"])
				rtxt=response.read()
				return rtxt
			else:
				return None
		else:
			return None
	def ClearReport(self,camp_id):
		reps=self.GetReportList(camp_id)
		for rep in reps:
			self.DeleteReport(int(rep))
		return None				
	def GetBanners(self,camp_id):
		arr=self.YaRequest('GetBanners',{"CampaignIDS" : [camp_id], "Filter": {"StatusShow": ["Yes"]}})
		return arr
	def GetBannerPhrases(self,banners):
		arr=self.YaRequest('GetBannerPhrases',banners)
		return arr
	def UpdatePrices(self,params):
		arr=self.YaRequest('UpdatePrices',params)
		return arr