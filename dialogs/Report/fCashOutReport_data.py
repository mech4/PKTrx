import com.ihsan.foundation.pobjecthelper as phelper
import simplejson
import sys

def FormSetDataEx(uideflist, params) :
  config = uideflist.config

  rec = uideflist.uipFilter.Dataset.AddRecord()
  rec.BranchCode = str(config.SecurityContext.GetUserInfo()[4])
  rec.BranchName = str(config.SecurityContext.GetUserInfo()[5])
  rec.BeginDate = (config.Now())
  rec.EndDate = rec.BeginDate
  rec.HeadOfficeCode = config.SysVarIntf.GetStringSysVar('OPTION','HeadOfficeCode')

def GetHistTransaction(config, params, returns):
  def AsDateTime(tdate):
    utils = config.ModLibUtils
    return utils.EncodeDate(tdate[0], tdate[1], tdate[2])

  helper = phelper.PObjectHelper(config)

  recParam = params.FirstRecord
  BeginDate = int(recParam.BeginDate)
  EndDate   = int(recParam.EndDate)
  BranchCode = recParam.BranchCode
  HeadOfficeCode = config.SysVarIntf.GetStringSysVar('OPTION','HeadOfficeCode')
  UserBranchCode = config.SecurityContext.GetUserInfo()[4]
  IsHeadOffice = (UserBranchCode == HeadOfficeCode)

  # Preparing returns

  if BeginDate == EndDate :
    PeriodStr = config.FormatDateTime('dd-mm-yyyy',BeginDate)
  else:
    PeriodStr = "%s s/d %s" % (
                   config.FormatDateTime('dd-mm-yyyy',BeginDate),
                   config.FormatDateTime('dd-mm-yyyy',EndDate)
                 )
  # end if
  
  
  NamaCabang = str(config.SecurityContext.GetUserInfo()[5])
  recSaldo = returns.CreateValues(
          ['PeriodStr',PeriodStr],
          ['NamaCabang',NamaCabang],
          ['TotalAmount',0.0]
        )
  
  dsHist = returns.AddNewDatasetEx(
      'ReportData',
    ';'.join([
      'TransactionItemId: integer',
      'TransactionDate: datetime',
      'TransactionDateStr: string',
      'TransactionNo: string',
      'ReferenceNo: string',
      'AccountNo: string',
      'AccountName: string',
      'Description: string',
      'CurrencyName: string',
      'Amount: float',
      'AmountEkuivalen: float',
      'Rate: float',
      'AuthStatus: string',
      'Channel:string',
      'FundEntity: string',
      'SponsorName: string',
      'BranchName: string',
      'Inputer: string',
      'TransactionType: string',
    ])
  )
  
  
  qParam = {}
  qParam['BDATE'] = config.FormatDateTime('yyyy-mm-dd', BeginDate)
  qParam['EDATE'] = config.FormatDateTime('yyyy-mm-dd', EndDate)

  # Additional condition query
  AddFilter = ''

  if recParam.IsAllBranch == 'F' :
    AddFilter = " and b.BranchCode='%s'" % BranchCode
  else:
    if not IsHeadOffice :
      UserBranchCode = config.SecurityContext.GetUserInfo()[4]
      SQLParam = "and ( b.BranchCode='%(BranchCode)s'  or b.MasterBranchCode='%(BranchCode)s' ) "
      AddFilter += SQLParam % {'BranchCode' : UserBranchCode}

  qParam['ADDFILTER'] = AddFilter
  
  sSQL = " select t.ActualDate, t.TransactionNo, t.ReferenceNo, \
        a.account_code as AccountNo ,a.account_name as AccountName, \
        t.Description, i.Amount, i.EkuivalenAmount,  t.Inputer,t.donorname, \
        t.AuthStatus, t.TransactionId, b.branchname, \
        (case when t.ChannelCode = 'R' then 'Kas Cabang' \
              when t.ChannelCode = 'P' then 'Kas Kecil' \
              when t.ChannelCode = 'A' then 'Bank' else 'Aktiva' end) as Channel , \
        '' as FundEntity, \
         i.transactionitemid ,\
         t.currencycode, i.currencycode, \
         t.rate, i.rate, d.short_name, e.short_name, \
         t.transactioncode \
      from transaction.transaction t, transaction.transactionitem i, \
        accounting.account a, branch b , \
        currency d, currency e \
      where t.transactionid = i.transactionid \
        and b.branchcode = i.branchcode \
        and ( \
          t.transactioncode = 'CO' \
          or ( \
            t.transactioncode in ('CAR','CARR','CARB') and \
            i.transactionitemtype = 'G' \
          ) \
        ) \
        and i.mutationtype='D' \
        and a.account_code = refaccountno \
        and t.ActualDate >= '%(BDATE)s' \
        and t.ActualDate <= '%(EDATE)s' \
        and t.CURRENCYCODE = d.CURRENCY_CODE \
        and i.CURRENCYCODE = e.CURRENCY_CODE \
        %(ADDFILTER)s\
        order by ActualDate, TransactionId " % qParam

  data  = config.CreateSQL(sSQL).rawresult

  TotalAmount = 0.0
  while not data.Eof:
    recData = dsHist.AddRecord()
    aDate = data.ActualDate
    recData.TransactionDateStr = '%2s-%2s-%4s' % (str(aDate[2]).zfill(2),
                                               str(aDate[1]).zfill(2),
                                               str(aDate[0]))
    recData.ReferenceNo = data.ReferenceNo
    recData.AccountNo = data.AccountNo
    recData.TransactionNo = data.TransactionNo
    recData.AccountName = data.AccountName
    recData.Description = data.Description

    TranCurrencyCode = data.CurrencyCode
    TranCurrencyName = data.Short_Name
    TransRate        = data.Rate
    ItemCurrencyCode = data.CurrencyCode_1
    ItemCurrencyName = data.Short_Name_1
    ItemRate        = data.Rate_1

    if TranCurrencyCode != ItemCurrencyCode  and ItemCurrencyCode == '000':
      CurrencyCode = TranCurrencyCode
      CurrencyName = TranCurrencyName
      Rate = TransRate
      Amount      = data.Amount / Rate
    else :
      CurrencyCode = ItemCurrencyCode
      CurrencyName = ItemCurrencyName
      Rate = ItemRate
      Amount = data.Amount
    # end if

    recData.Amount = Amount
    recData.AmountEkuivalen = data.EkuivalenAmount
    recData.Rate = Rate
    recData.CurrencyName = TranCurrencyName

    recData.Inputer = data.Inputer
    recData.Authstatus  = data.AuthStatus
    recData.Channel  = data.Channel[:20]
    recData.FundEntity = data.FundEntity
    recData.SponsorName = ''
    recData.BranchName = data.BranchName
    recData.TransactionType = data.TransactionCode

    TotalAmount += data.EkuivalenAmount

    data.Next()
  # end while

  recSaldo.TotalAmount = TotalAmount
  
