# -*- coding: utf-8 -*-
from tipfy.app import Response
from tipfy.handler import RequestHandler
from tipfyext.jinja2 import Jinja2Mixin
from directapi import YaObject,YaCampany,YaReport,YaCampanyLogs
from datetime import timedelta, date, datetime
from xml.dom.minidom import parseString
from google.appengine.ext import db
from google.appengine.api.labs import taskqueue
from google.appengine.api import memcache, mail
import json, logging

_timezone=timedelta(hours=4)
ya_login="luk-direct"
ya_pass="Wq21150i"
ya_token="605de565b31f4063aa0ba11d9adb5dc1"
ya_stoket="dddd7371f0f9456a915c61f0e859009c"

def implode(lists):
	str=""
	for key in lists:
		str+=","+key
	return str[1:]

def sort_stat(x,y):
	if (x["sum"] > y["sum"]):
		return -1
	if (x["sum"] < y["sum"]):
		return 1
	if (x["shows"] > y["shows"]):
		return -1
	if (x["shows"] < y["shows"]):
		return 1
	if (x["shows"] == y["shows"]):
		return 0

def sort_camp(x,y):
	if ((x["StatusShow"]=="Yes") and (y["StatusShow"]!="Yes")):
		return -1
	if ((x["StatusShow"]!="Yes") and (y["StatusShow"]=="Yes")):
		return 1
	if (int(x["todayPercent"])>int(y["todayPercent"])):
		return -1
	if (int(x["todayPercent"])<int(y["todayPercent"])):
		return 1
	if (x["Rest"]>y["Rest"]):
		return -1
	if (x["Rest"]<y["Rest"]):
		return 1
	if (x["Rest"]==y["Rest"]):
		return 0


class mcacher():
	def __init__(self):
		self.cache={}
	def get(self,key):
		if key in self.cache:
			logging.debug('hit cache ok %s'%key)
			return self.cache[key]
		else:
			logging.debug('hit cache failed %s'%key)
			return None
	def set(self,key,val):
		self.cache[key]=val


mycacher=mcacher()

def getSysCamps():
	tcamps=mycacher.get("syscamps")
	if tcamps is None:
		camps=YaCampany.all()
		mycacher.set("camps",camps)
		tcamps={}
		for camp in camps:
			tcamps[camp.camp_id]=camp
		mycacher.set("syscamps",tcamps)
	return tcamps

def resetSysCamps():
	camps=YaCampany.all()
	mycacher.set("camps",camps)
	tcamps={}
	for camp in camps:
		tcamps[camp.camp_id]=camp
	mycacher.set("syscamps",tcamps)	

def getCampByID(camp_id):
	tcamps=mycacher.get("syscamps")
	if tcamps is None:
		camps=YaCampany.all()
		mycacher.set("camps",camps)
		tcamps={}
		for camp in camps:
			tcamps[camp.camp_id]=camp
		mycacher.set("syscamps",tcamps)
		logging.debug('failed cache tcamps')
	else:
		logging.debug('hit cache tcamps')
	
	return tcamps.get(str(camp_id),None)
	
class StopCampaignHandler(RequestHandler, Jinja2Mixin):
    def get(self):
	cid=self.request.args.get('camp_id')
	obj=mycacher.get("obj")
	if obj is None:
		obj=YaObject(ya_login,ya_pass,ya_token,ya_stoken)
		mycacher.set("obj",obj)
	arr=obj.StopCampaign(cid)
	memcache.delete("camps2")
	return self.redirect('/')

class StartCampaignHandler(RequestHandler, Jinja2Mixin):
    def get(self):
	cid=self.request.args.get('camp_id')
	obj=mycacher.get("obj")
	if obj is None:
		obj=YaObject(ya_login,ya_pass,ya_token,ya_stoken)
		mycacher.set("obj",obj)
	obj.ResumeCampaign(cid)
	memcache.delete("camps2")
	return self.redirect('/')

class ChangeControlHandler(RequestHandler, Jinja2Mixin):
    def post(self):
	cid=self.request.form.get('camp_id')
	sum=int(self.request.form.get('change_control'))
	yacamps = getCampByID(cid)
	if yacamps is None:
		yacamps = YaCampany(camp_id=str(cid),amount=sum,key_name=str(cid))
		yacamps.put()
		resetSysCamps()
	return Response(str(cid)+'_'+str(sum))
class CreateInvoiceHandler(RequestHandler, Jinja2Mixin):
    def post(self):
	cid=int(self.request.form.get('get_invoice'))
	amn=round(float(self.request.form.get('amount'))/30,4)
	td=datetime.today()+_timezone
	opnum=td.year*365*60*60+td.month*30*60*60+td.day*60*60+td.hour*60+td.minute
	yacamps = getCampByID(cid)
	if yacamps is None:
		yacamps = YaCampany(camp_id=str(cid),amount=0,key_name=str(cid))
		yacamps.put()
		resetSysCamps()
#	logging.debug('create invoice '+str(cid)+' amount '+str(amn))
	yacamps.last_invoice=int(amn*30)
	yacamps.put()
	obj=mycacher.get("obj")
	if obj is None:
		obj=YaObject(ya_login,ya_pass,ya_token,ya_stoken)
		mycacher.set("obj",obj)
	logging.debug('create invoice '+str(cid)+', amount '+str(amn))
	ret=obj.CreateInvoice(cid,amn,opnum)
	logging.debug('invoice url '+ret)
	memcache.delete("ams")
	return Response(ret)
class ControlCampaignHandler(RequestHandler, Jinja2Mixin):
    def post(self):
	camp_id=self.request.form.get('camp_id')
	amn=float(self.request.form.get('amount'))
	plan=float(self.request.form.get('plan'))
	logging.debug('current amount '+str(amn)+', total amount '+str(plan))
	plan2=plan*0.9
	obj=mycacher.get("obj")
	if obj is None:
		obj=YaObject(ya_login,ya_pass,ya_token,ya_stoken)
		mycacher.set("obj",obj)
	param=obj.GetCampaignParams(camp_id)

	if amn>plan2:
		cd=datetime.today()+_timezone
		if param["StatusShow"]=="Yes":
			logging.debug('Stop campaign '+camp_id)
			obj.StopCampaign(camp_id)
			yacamps = getCampByID(camp_id)
			report=YaCampanyLogs(camp_id=yacamps,amount=int(amn),plan=int(plan),act="stop")
			report.put()
			memcache.delete("stopd"+cd.strftime("%Y-%m-%d"))
			memcache.delete("camps2")
			memcache.delete("stoped")
		memcache.set("stop_camp_"+str(camp_id)+"_date_"+cd.strftime("%Y-%m-%d"),amn,7200)
		logging.debug("stop_camp_"+str(camp_id)+"_date_"+cd.strftime("%Y-%m-%d"))
	else:
		if (plan>0) and (param["StatusShow"]=="No"):
			dt=datetime.today()+_timezone
			if dt.hour<10:
				logging.debug('Start campaign '+camp_id)
				obj.ResumeCampaign(camp_id)
				yacamps = getCampByID(camp_id)
				report=YaCampanyLogs(camp_id=yacamps,amount=int(amn),plan=int(plan),act="start")
				report.put()
				memcache.delete("stopd"+dt.strftime("%Y-%m-%d"))
				memcache.delete("camps2")
				memcache.delete("stoped")
	return Response('1')
class UpdateStatHandler(RequestHandler, Jinja2Mixin):
	def get(self):
		logging.debug('1Start campanies update stat')
		camps=getSysCamps()
		camp_id=[camps[camp].camp_id for camp in camps]
		amn={}
		for camp in camps:
			amn[int(camps[camp].camp_id)]=camps[camp].amount

		td=datetime.today()+_timezone
		obj=mycacher.get("obj")
		if obj is None:
			obj=YaObject(ya_login,ya_pass,ya_token,ya_stoken)
			mycacher.set("obj",obj)
		cmps=obj.GetCampaignsParams(camp_id)
		camp_id=[str(cmp_id) for cmp_id in cmps if (cmps[cmp_id]["Rest"]>0) and (min(cmps[cmp_id]["TimeTarget"]["DaysHours"][0]["Hours"])<=td.hour) and (cmps[cmp_id]["Status"]!=u'Кампания остановлена')]
		logging.debug('count campanies %d'%len(camp_id))
		taskqueue.add(url='/updatecampanystat', params={'camp_id': implode(camp_id)})

		camp_ids=[cmp_id for cmp_id in cmps if (cmps[cmp_id]["Rest"]>0) and (min(cmps[cmp_id]["TimeTarget"]["DaysHours"][0]["Hours"])>td.hour)]
		for camp_id in camp_ids:
			if cmps[camp_id]["StatusShow"]=="No":
				taskqueue.add(url='/controlcampaign', params={'camp_id': camp_id, "plan": amn[camp_id], "amount": 0})
		return Response('1')
class UpdateRestHandler(RequestHandler, Jinja2Mixin):
	def get(self):
		camps=getSysCamps()
		camp_id=[camps[camp].camp_id for camp in camps]
		obj=mycacher.get("obj")
		if obj is None:
			obj=YaObject(ya_login,ya_pass,ya_token,ya_stoken)
			mycacher.set("obj",obj)
		cmps=obj.GetCampaignsParams(camp_id)
		for camp in camps:
			if camps[camp].last_rest is None:
				camps[camp].last_rest=0.0
			if camps[camp].last_rest<cmps[int(camps[camp].camp_id)]["Rest"]:
				logging.debug('New payment in campany '+str(camps[camp].camp_id)+' amount '+str(cmps[int(camps[camp].camp_id)]["Rest"]-camps[camp].last_rest))
				mail.send_mail(sender="LS robot <admin@luk-studio.ru>",to="admin@luk-studio.ru, sp@luk-studio.ru, krylova@luk-studio.ru",subject=u'Пополнение рекламной кампании %s'%cmps[int(camps[camp].camp_id)]["Name"],body=u'Произошло пополение рекламной кампании %s на сумму около %s ye'%(cmps[int(camps[camp].camp_id)]["Name"],str(cmps[int(camps[camp].camp_id)]["Rest"]-camps[camp].last_rest)))
			camps[camp].last_rest=float(cmps[int(camps[camp].camp_id)]["Rest"])
			camps[camp].put()
		return Response('1')
class UpdateCampanyStatHandler(RequestHandler, Jinja2Mixin):
    def parseResponse(self,resp):
	dom=parseString(resp)
	rows=dom.getElementsByTagName("phrase")
	dicts={}
	for row in rows:
		dicts[row.getAttribute("phraseID")]=row.getAttribute("value")

	rows=dom.getElementsByTagName("row")
	logging.debug('count xml rows '+str(len(rows)))
	out={}
	for row in rows:
		stat={"sum_search":"","sum_context":"","shows_search":"","shows_context":"","clicks_search":"","clicks_context":"","sum":"","shows":"","clicks":""}
		for key in stat:
			stat[key]=row.getAttribute(key)
		sdate=row.getAttribute("statDate")
		if sdate not in out:
			out[sdate]={"items": {}}
		phrID=row.getAttribute("phraseID")
		out[sdate]["items"][phrID]=stat
		out[sdate]["dicts"]=dicts
	return out
	
    def post(self):
	obj=mycacher.get("obj")
	if obj is None:
		obj=YaObject(ya_login,ya_pass,ya_token,ya_stoken)
		mycacher.set("obj",obj)
	_camps=self.request.form.get('camp_id')
	camps=_camps.split(",")
	camp_id=camps[0]
	logging.debug('Start camp_id stat='+camp_id)
	yacamps = getCampByID(camp_id)
	if yacamps is None:
		if len(camps)>1:
			taskqueue.add(url='/updatecampanystat', params={'camp_id': implode(camps[1:])})
			logging.debug('start new camps '+implode(camps[1:]))
		else:
			memcache.delete("stats")
		return Response('1')

	end_date=datetime.today()+_timezone
	end_date_str=end_date.strftime("%Y-%m-%d")
	cnt_days=memcache.get("camp_id_"+str(camp_id)+"_date_"+end_date_str)

	if cnt_days is None or cnt_days>0:
		cnt_days=15
		res=db.GqlQuery("select * from YaReport where camp_id=:1 and rtype=0 order by date DESC",yacamps)
		cnt=res.count()
		if cnt!=0:
			items=res.fetch(1)
			for item in items:
				cd=item.date

			dd1=date(end_date.year,end_date.month,end_date.day)
			td=dd1-cd
			cnt_days=td.days-1
		if cnt_days<0:
			cnt_days=0
		memcache.set("camp_id_"+str(camp_id)+"_date_"+end_date_str,cnt_days,7200)
	else:
		if cnt_days<0:
			cnt_days=0

	logging.debug('count days '+str(cnt_days))
	start_date=end_date-timedelta(days=cnt_days)
	rep_id=obj.CreateNewReport(camp_id,start_date.strftime("%Y-%m-%d"),end_date_str,["clDate","clPhrase"])

	if rep_id is None:
		logging.debug('Clear report')
		obj.ClearReport(camp_id)
		rep_id=obj.CreateNewReport(camp_id,start_date.strftime("%Y-%m-%d"),end_date_str,["clDate","clPhrase"])
		if rep_id is None:
			logging.debug('error in creating report')
		else:
			logging.debug('create report id '+str(rep_id))
	else:
		logging.debug('create report id '+str(rep_id))

	rtxt=obj.GetReport(camp_id,rep_id)
	obj.DeleteReport(rep_id)

	if rtxt is not None:
		out=self.parseResponse(rtxt)
	else:
		logging.debug('error in reading report')
		out={}
	logging.debug('count stat rows '+str(len(out)))
	for sdate in out:
		logging.debug('save date '+str(sdate))
		notrel={"shows_search": 0.0,"shows_context": 0.0,"clicks_search": 0.0,"clicks_context": 0.0}
		tmp={"sum_search": 0.0,"sum_context": 0.0,"shows_search": 0.0,"shows_context": 0.0,"clicks_search": 0.0,"clicks_context": 0.0}
		for phr in out[sdate]["items"]:
			if phr!=1:
				for key in notrel:
					notrel[key]+=float(out[sdate]["items"][phr][key])
		for key in tmp:
			tmp[key]=sum(float(out[sdate]["items"][phr][key]) for phr in out[sdate]["items"])
		for key in notrel:
			tmp[key+"_notrel"]=notrel[key]
		_dicts=json.dumps(out[sdate]["dicts"])
		full_report=json.dumps(out[sdate]["items"], ensure_ascii=False).encode('utf8')
		short_report=json.dumps(tmp, ensure_ascii=False).encode('utf8')
		d1=sdate.split("-")
		cd=date(int(d1[0]),int(d1[1]),int(d1[2]))
		rt=0
		sstop=memcache.get("stop_camp_"+str(camp_id)+"_date_"+sdate)
		if (sdate==end_date_str) and ((sstop is None) or (sstop<yacamps.amount)) and ((float(tmp["sum_search"])+float(tmp["sum_context"]))>(float(yacamps.amount/2))):
			rt=1
			taskqueue.add(url='/controlcampaign', params={'camp_id': camp_id, "plan": yacamps.amount, "amount": (float(tmp["sum_search"])+float(tmp["sum_context"]))})
			yacamps.last_amount=int(float(tmp["sum_search"])+float(tmp["sum_context"]))
			yacamps.put()
		report=YaReport(camp_id=yacamps,date=cd,rtype=rt,rep=full_report,shortrep=short_report,dicts=_dicts,key_name=(camp_id+"_"+sdate))
		report.put()
	if ((end_date_str not in out) or (len(out)==0)) and (yacamps.amount>0):
		if yacamps.last_amount!=0:
			yacamps.last_amount=0
			yacamps.put()
		param=obj.GetCampaignParams(camp_id)
		if param["StatusShow"]=="No":
			taskqueue.add(url='/controlcampaign', params={'camp_id': camp_id, "plan": yacamps.amount, "amount": 0})
	if len(camps)>1:
		taskqueue.add(url='/updatecampanystat', params={'camp_id': implode(camps[1:])})
	else:
		memcache.delete("stats")
	return Response('1')
class SaveCampaignHandler(RequestHandler, Jinja2Mixin):
    def post(self):
	arr=self.request.form.get('arr')
	res=json.loads(arr)
	param=[]
	for key in res:
		phrid,campid,banid,value=key
		param.append({"PhraseID":phrid,"BannerID":banid,"CampaignID":campid,"Price":value,"AutoBroker":"Yes"})
	obj=mycacher.get("obj")
	if obj is None:
		obj=YaObject(ya_login,ya_pass,ya_token,ya_stoken)
		mycacher.set("obj",obj)
	obj.UpdatePrices(param)
	return Response('1')
class CampaignHandler(RequestHandler, Jinja2Mixin):
    def get(self):
	camp_id=int(self.request.args.get('cid'))
	obj=mycacher.get("obj")
	if obj is None:
		obj=YaObject(ya_login,ya_pass,ya_token,ya_stoken)
		mycacher.set("obj",obj)
	banners=obj.GetBanners(camp_id)
	phrs=obj.GetBannerPhrases([key["BannerID"] for key in banners])
	bans={}
	for ban in banners:
		bans[ban["BannerID"]]=ban

	for phr in phrs:
		phr["Phrase"]=phr["Phrase"].split("-")[0]
		if phr["Shows"]>0:
			phr["ctr"]=round(phr["Clicks"]/phr["Shows"]*100,2)
		else:
			phr["ctr"]=0
		bans[phr["BannerID"]]["items"]=bans[phr["BannerID"]].get("items",[])
		bans[phr["BannerID"]]["items"].append(phr)		
        context = {
            'bans': bans.values()
        }
        return self.render_response('campaign.html', **context)
class FlushMemcacheHandler(RequestHandler, Jinja2Mixin):
    def get(self):
	memcache.flush_all()
	return Response('1')
class GetStatHandler(RequestHandler, Jinja2Mixin):
    def get(self):
	camp_id=str(self.request.args.get('cid'))
	interval=self.request.args.get('int')

	obj=mycacher.get("obj")
	if obj is None:
		obj=YaObject(ya_login,ya_pass,ya_token,ya_stoken)
		mycacher.set("obj",obj)
	yacamps = getCampByID(camp_id)
	dicts={}
	stats=[]
	if interval=="yestoday":
		res=YaReport.all()
		res.filter("date > ",(datetime.today()-timedelta(days=2)+_timezone))
		res.filter("camp_id",yacamps)
		data=json.loads(res[0].rep)
		_dicts=json.loads(res[0].dicts)
		for key in _dicts:
			dicts[key]=_dicts[key]
		_data={}
		for key in data:
			_data[dicts[key]]=data[key]
		stats.append(_data)
	else:
		res=YaReport.all()
		res.filter("date >=",(datetime.today()-timedelta(days=8)+_timezone))
		res.filter("camp_id",yacamps)

		for stat in res:
			data=json.loads(stat.rep)
			_dicts=json.loads(stat.dicts)
			for key in _dicts:
				dicts[key]=_dicts[key]
			_data={}
			for key in data:
				_data[dicts[key]]=data[key]
			stats.append(_data)
	out={}
	for d in stats:
		for banid in d:
			out[banid]=out.get(banid,{})
			for p in d[banid]:
				out[banid][p]=out[banid].get(p,0.0)
				out[banid][p]+=float(d[banid][p])

	total={"sum": 0.0,"shows": 0.0,"clicks": 0.0,"sum_search": 0.0,"sum_context": 0.0,"clicks_search": 0.0,"clicks_context": 0.0,"shows_search": 0.0,"shows_context": 0.0}
	for p in total:
		total[p]=sum(out[banid][p] for banid in out)

	if total["clicks_search"]>0:
		total["per_search"]=round(total["sum_search"]/total["clicks_search"],2)
	else:
		total["per_search"]=0.0
	if total["clicks_context"]>0:
		total["per_context"]=round(total["sum_context"]/total["clicks_context"],2)
	else:
		total["per_context"]=0.0
	if total["clicks"]>0:
		total["per"]=round(total["sum"]/total["clicks"],2)
	else:
		total["per"]=0.0
	if total["shows"]>0:
		total["ctr"]=round(total["clicks_search"]/total["shows_search"]*100,2)
	else:
		total["ctr"]=0.0

	for banid in out:
		out[banid]["name"]=banid.split("-")[0]
		if out[banid]["clicks_search"]>0:
			out[banid]["per_search"]=round(out[banid]["sum_search"]/out[banid]["clicks_search"],2)
		else:
			out[banid]["per_search"]=0.0
		if out[banid]["clicks_context"]>0:
			out[banid]["per_context"]=round(out[banid]["sum_context"]/out[banid]["clicks_context"],2)
		else:
			out[banid]["per_context"]=0.0
		if out[banid]["clicks"]>0:
			out[banid]["per"]=round(out[banid]["sum"]/out[banid]["clicks"],2)
		else:
			out[banid]["per"]=0.0

		if out[banid]["shows"]>0:
			out[banid]["ctr"]=round(out[banid]["clicks"]/out[banid]["shows"]*100,2)
		else:
			out[banid]["ctr"]=0.0

		if total["sum"]>0:
			out[banid]["psum"]=round(out[banid]["sum"]/total["sum"]*100,2)
		else:
			out[banid]["psum"]=0.0

	tcamps=out.values()
	tcamps.sort(sort_stat)
        context = {
            'camps': tcamps,
	    'total': total
        }	
        return self.render_response('stat.html', **context)
class IndexHandler(RequestHandler, Jinja2Mixin):
    def get(self):
	ddd=datetime.today()
	cd=(ddd+_timezone).strftime("%Y-%m-%d")
	dates=[]
	for key in range(14):
		if ((ddd-timedelta(days=key)+_timezone).weekday() not in (5,6)) or key in [0,1]:
			t1=(ddd-timedelta(days=key)+_timezone)
			dates.append(t1.strftime("%Y-%m-%d"))

	end_date=dates[0]
	start_date=dates[-1]
	obj=mycacher.get("obj")
	if obj is None:
		obj=YaObject(ya_login,ya_pass,ya_token,ya_stoken)
		mycacher.set("obj",obj)

	camps=memcache.get("camps2")
	if camps is None:
		logins=obj.GetClientsList()
		camps=obj.GetCampaignsList(logins)
		memcache.set("camps2",camps,7200)
	camps_ids=[key for key in camps]

	ams=getSysCamps()
	for am in ams:
		if int(ams[am].camp_id) in camps:
			camps[int(ams[am].camp_id)]["control_money"]=ams[am].amount
			camps[int(ams[am].camp_id)]["last_invoice"]=ams[am].last_invoice
			
	stats=memcache.get("stats")
	if stats is None:
		res=YaReport.all()
		res.filter("date >=",(ddd-timedelta(days=14)+_timezone))
		res.order("date")
		stats=[]
		for stat in res:
			data=json.loads(stat.shortrep)
			stats.append({"CampaignID": stat.camp_id.camp_id,"StatDate": stat.date.strftime("%Y-%m-%d"),"SumSearch": data["sum_search"],"SumContext": data["sum_context"],"ClicksSearch": data["clicks_search"],"ClicksContext": data["clicks_context"],"ShowsSearch": data["shows_search"],"ShowsContext": data["shows_context"],"ClicksSearchNotrel": data["clicks_search_notrel"],"ClicksContextNotrel": data["clicks_context_notrel"],"ShowsSearchNotrel": data["shows_search_notrel"],"ShowsContextNotrel": data["shows_context_notrel"]})
		memcache.set("stats",stats,500)
	stopd=memcache.get("stopd"+cd)
	if stopd is None:
		res=YaCampanyLogs.all()
		dt2=ddd+_timezone
		dt3=date(year=dt2.year,month=dt2.month,day=dt2.day)
		res.filter("date >=",dt3)
		res.filter("act","stop")
		stopd=[]
		for act in res:
			stopd.append({'camp_id': int(act.camp_id.camp_id),'date': act.date})
		memcache.set("stopd"+cd,stopd,10800)
	for act in stopd:
		camps[int(act["camp_id"])]["stop"]="%02d"%(act["date"].hour+4)+":%02d"%act["date"].minute

	stoped=memcache.get("stoped")
	if stoped is None:
		stoped={}
		res2=YaCampanyLogs.all()
		dt2=ddd+_timezone-timedelta(days=14)
		dt3=date(year=dt2.year,month=dt2.month,day=dt2.day)
		res2.filter("date >=",dt3)
		res2.filter("act","stop")
		for act in res2:
			d1=str(act.date.year)+"-"+"%02d"%act.date.month+"-"+"%02d"%act.date.day
			t1=[act.date.hour+4,act.date.minute,0]
			stoped[int(act.camp_id.camp_id)]=stoped.get(int(act.camp_id.camp_id),{})
			stoped[int(act.camp_id.camp_id)][d1]=t1
		memcache.set("stoped",stoped,14400)
	ostat={}
	for key in stats:
		ostat[int(key["CampaignID"])]=ostat.get(int(key["CampaignID"]),{})
		ostat[int(key["CampaignID"])][key["StatDate"]]=key
	for campid in camps:
		_sum={"SumSearch":0,"SumContext":0,"ClicksSearch":0,"ClicksContext":0,"ShowsSearch":0,"ShowsContext":0,"PerClickSearch":0,"PerClickContext":0,"PerClickTotal":0,"CTR":0}
		graph={}
		ostat[campid]=ostat.get(campid,{})
		total_d=sum(1 for dt in dates if dt in ostat[campid])
		for dt in dates:
			ostat[campid][dt]=ostat[campid].get(dt,{"SumSearch":0,"SumContext":0,"ClicksSearch":0,"ClicksContext":0,"ShowsSearch":0,"ShowsContext":0,"PerClickSearch":0,"PerClickContext":0,"PerClickTotal":0,"ClicksSearchNotrel":0,"ShowsSearchNotrel":0})

			if ostat[campid][dt]["ShowsSearchNotrel"]>0:
				ostat[campid][dt]["CTR"]=round(ostat[campid][dt]["ClicksSearchNotrel"]/ostat[campid][dt]["ShowsSearchNotrel"]*100,2)
			else:
				ostat[campid][dt]["CTR"]=0;

			if ostat[campid][dt]["ClicksSearch"]>0:
				ostat[campid][dt]["PerClickSearch"]=round(ostat[campid][dt]["SumSearch"]/ostat[campid][dt]["ClicksSearch"],2)
			else:
				ostat[campid][dt]["PerClickSearch"]=0;
			if ostat[campid][dt]["ClicksContext"]>0:
				ostat[campid][dt]["PerClickContext"]=round(ostat[campid][dt]["SumContext"]/ostat[campid][dt]["ClicksContext"],2)
			else:
				ostat[campid][dt]["PerClickContext"]=0;
			if (ostat[campid][dt]["ClicksSearch"]+ostat[campid][dt]["ClicksContext"])>0:
				ostat[campid][dt]["PerClickTotal"]=round((ostat[campid][dt]["SumContext"]+ostat[campid][dt]["SumSearch"])/(ostat[campid][dt]["ClicksSearch"]+ostat[campid][dt]["ClicksContext"]),2)
			else:
				ostat[campid][dt]["PerClickTotal"]=0;
			
			tdt=dt.split("-")
		for param in _sum:
			_sum[param]=sum(ostat[campid][dt][param] for dt in dates)
		graph["sum"]=[[dt,round(ostat[campid][dt]["SumSearch"],2),round(ostat[campid][dt]["SumContext"],2),round(ostat[campid][dt]["SumSearch"]+ostat[campid][dt]["SumContext"],2)] for dt in dates]
		graph["clicks"]=[[dt,ostat[campid][dt]["ClicksSearch"],ostat[campid][dt]["ClicksContext"],ostat[campid][dt]["ClicksSearch"]+ostat[campid][dt]["ClicksContext"]] for dt in dates]
		graph["shows"]=[[dt,ostat[campid][dt]["ShowsSearch"],ostat[campid][dt]["ShowsContext"],ostat[campid][dt]["ShowsSearch"]+ostat[campid][dt]["ShowsContext"]] for dt in dates]
		graph["per"]=[[dt,ostat[campid][dt]["PerClickSearch"],ostat[campid][dt]["PerClickContext"],ostat[campid][dt]["PerClickTotal"]] for dt in dates]
		graph["ctr"]=[[dt,ostat[campid][dt]["CTR"]] for dt in dates]
		stoped[campid]=stoped.get(campid,{})
		graph["stop"]=[[dt,stoped[campid].get(dt,[23,59,59])] for dt in dates]

		for key in graph:
			graph[key]=json.dumps(graph[key])
		for key in ("SumSearch","SumContext","ClicksSearch","ClicksContext","ShowsSearch","ShowsContext","CTR"):
			if total_d>0:
				_sum[key]=round(_sum[key]/total_d,2)
			else:
				_sum[key]=round(0,2)	
		camps[campid]["graph"]=graph
		camps[campid]["SumTotal"]=_sum["SumSearch"]+_sum["SumContext"]
		camps[campid]["SumContext"]=_sum["SumContext"]
		camps[campid]["CTR"]=_sum["CTR"]
		camps[campid]["ClicksTotal"]=int(_sum["ClicksSearch"]+_sum["ClicksContext"])
		camps[campid]["ClicksContext"]=int(_sum["ClicksContext"])
		camps[campid]["ShowsTotal"]=int(_sum["ShowsSearch"]+_sum["ShowsContext"])
		camps[campid]["ShowsContext"]=int(_sum["ShowsContext"])
		if (camps[campid]["SumTotal"]>0):
			camps[campid]["days_rest"]=int(camps[campid]["Rest"]/camps[campid]["SumTotal"])
		else:
			camps[campid]["days_rest"]=0
		if (_sum["ClicksContext"]+_sum["ClicksSearch"])>0:
			camps[campid]["PerClickTotal"]=round((_sum["SumContext"]+_sum["SumSearch"])/(_sum["ClicksContext"]+_sum["ClicksSearch"]),2)
		else:
			camps[campid]["PerClickTotal"]=0
		camps[campid]["todaySumTotal"]=ostat[campid][dates[0]]["SumSearch"]+ostat[campid][dates[0]]["SumContext"]
		camps[campid]["yestodaySumTotal"]=ostat[campid][dates[1]]["SumSearch"]+ostat[campid][dates[1]]["SumContext"]
		camps[campid]['control_money']=camps[campid].get('control_money',0)

		if (camps[campid]["control_money"] > 0):
			camps[campid]["todayPer"]=int(30*((100-100*camps[campid]["todaySumTotal"]/camps[campid]["control_money"])/100))
			camps[campid]["todayPercent"]=int(round(100*camps[campid]["todaySumTotal"]/camps[campid]["control_money"]))
			if (camps[campid]["todayPercent"]>100):
				camps[campid]["todayPer"]=0
		else:
			camps[campid]["todayPer"]=100
			camps[campid]["todayPercent"]=0
		camps[campid]["todaySumContext"]=ostat[campid][dates[0]]["SumContext"]
		camps[campid]["yestodaySumContext"]=ostat[campid][dates[1]]["SumContext"]

		camps[campid]["todayCTR"]=ostat[campid][dates[0]]["CTR"]
		camps[campid]["yestodayCTR"]=ostat[campid][dates[1]]["CTR"]

		camps[campid]["todayClicksSearch"]=int(ostat[campid][dates[0]]["ClicksSearch"]+ostat[campid][dates[0]]["ClicksContext"])
		camps[campid]["yestodayClicksSearch"]=int(ostat[campid][dates[1]]["ClicksSearch"]+ostat[campid][dates[1]]["ClicksContext"])
		camps[campid]["todayClicksContext"]=int(ostat[campid][dates[0]]["ClicksContext"])
		camps[campid]["yestodayClicksContext"]=int(ostat[campid][dates[1]]["ClicksContext"])
		camps[campid]["todayShowsSearch"]=int(ostat[campid][dates[0]]["ShowsSearch"]+ostat[campid][dates[0]]["ShowsContext"])
		camps[campid]["yestodayShowsSearch"]=int(ostat[campid][dates[1]]["ShowsSearch"]+ostat[campid][dates[1]]["ShowsContext"])
		camps[campid]["todayShowsContext"]=int(ostat[campid][dates[0]]["ShowsContext"])
		camps[campid]["yestodayShowsContext"]=int(ostat[campid][dates[1]]["ShowsContext"])
	
		if (camps[campid]["todayClicksSearch"]+camps[campid]["todayClicksContext"])>0:
			camps[campid]["todayPerClick"]=round((camps[campid]["todaySumTotal"])/(camps[campid]["todayClicksSearch"]),2)
		else:
			camps[campid]["todayPerClick"]=0
	
		if (camps[campid]["yestodayClicksSearch"]+camps[campid]["yestodayClicksContext"])>0:
			camps[campid]["yestodayPerClick"]=round((camps[campid]["yestodaySumTotal"])/(camps[campid]["yestodayClicksSearch"]),2)
		else:
			camps[campid]["yestodayPerClick"]=0
	
		if (camps[campid]["todayPerClick"]<camps[campid]["PerClickTotal"]) and (camps[campid]["yestodayPerClick"]<camps[campid]["PerClickTotal"]):
			camps[campid]["trend"]="up"
		elif (camps[campid]["todayPerClick"]>camps[campid]["PerClickTotal"]) and (camps[campid]["yestodayPerClick"]>camps[campid]["PerClickTotal"]):
			camps[campid]["trend"]="down"
		else:
			camps[campid]["trend"]="zero"

		camps[campid]["Rest"]=int(camps[campid]["Rest"])

	tcamps=camps.values()
	tcamps.sort(sort_camp)

        context = {
            'camps': tcamps,
        }

        return self.render_response('index.html', **context)