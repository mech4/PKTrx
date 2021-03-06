import com.ihsan.foundation.pobjecthelper as phelper
import simplejson
import sys

def FormSetDataEx(uideflist, params) :
  config = uideflist.config

  rec = uideflist.uipEmployeeAR.Dataset.AddRecord()
  rec.BranchCode = str(config.SecurityContext.GetUserInfo()[4])
  rec.BranchId = int(config.SecurityContext.GetUserInfo()[2])

  Now = config.Now()
  
  y = config.ModLibUtils.DecodeDate(Now)[0]
  rec.BeginDate = config.ModLibUtils.EncodeDate(y,1,1)
  rec.EndDate = int(Now)
  
def GetCABalance(config, aEmployeeId, aDate = None):

  strSQL = "select sum(case when a.mutationtype='D' then a.EkuivalenAmount \
                         else -a.EkuivalenAmount \
                    end) \
            from transactionitem a, transaction b, \
                 accounttransactionitem c, accountreceivable d\
            where a.transactionid=b.transactionid \
               and a.transactionitemid=c.transactionitemid \
               and c.accountno = d.accountno \
               and employeeidnumber = %d " % aEmployeeId

  if aDate != None :
    FormattedDate = config.FormatDateTime('yyyy-mm-dd',aDate)
    strSQL += " and b.actualdate < '%s' " % FormattedDate

  resSQL = config.CreateSQL(strSQL).rawresult

  return resSQL.GetFieldValueAt(0) or 0.0

def GetCashAdvanceBalance(config, params, returns):
  status = returns.CreateValues(
    ['IsErr' , 0],
    ['ErrMessage', ''],
    ['Balance', 0.0]
  )
  
  try:
    EmployeeId = params.FirstRecord.EmployeeId
    status.Balance = GetCABalance(config, EmployeeId)

  except:
    status.IsErr = 1
    status.ErrMessage = str(sys.exc_info()[1])

def GetHistTransaction(config, params, returns):
  def AsDateTime(tdate):
    utils = config.ModLibUtils
    return utils.EncodeDate(tdate[0], tdate[1], tdate[2])

  helper = phelper.PObjectHelper(config)

  rec = params.FirstRecord
  EmployeeId = rec.EmployeeId
  BeginDate = int(rec.BeginDate)
  EndDate   = int(rec.EndDate)

  sqlBeginDateParam = config.FormatDateTime('yyyy-mm-dd',BeginDate)
  sqlEndDateParam = config.FormatDateTime('yyyy-mm-dd',EndDate + 1)


  # Preparing returns
  
  #AccountReceivable = helper.GetObject('EmployeeAccountReceivable',AccountNo)
  #BeginningBalance = 0.0 #AccountReceivable.GetBalanceByDate(BeginDate)
  BeginningBalance = GetCABalance(config, EmployeeId, BeginDate)
  

  if BeginDate == EndDate :
    PeriodStr = config.FormatDateTime('dd-mm-yyyy',BeginDate)
  else:
    PeriodStr = "%s s/d %s" % (
                   config.FormatDateTime('dd-mm-yyyy',BeginDate),
                   config.FormatDateTime('dd-mm-yyyy',EndDate)
                 )
  # end if

  recSaldo = returns.CreateValues(
          ['BeginningBalance', BeginningBalance or 0.0],
          ['PeriodStr',PeriodStr],
          ['TotalDebet',0.0],
          ['TotalCredit',0.0],
          ['TotalBalance',BeginningBalance or 0.0],
        )

  #--- GET HISTORI TRANSAKSI
  dsHist = returns.AddNewDatasetEx(
    'histori',
    ';'.join([
      'TransactionItemId: integer',
      'TransactionDate: datetime',
      'TransactionDateStr: string',
      'TransactionCode: string',
      'MutationType: string',
      'Amount: float',
      'AmountEkuivalen: float',
      'CurrencyName: string',
      'Rate: float',
      'Debet: float',
      'Kredit: float',
      'ReferenceNo: string',
      'Description: string',
      'Inputer: string',
      'TransactionNo:string',
      'Total:float',
      'AuthStatus:string',
      'ReturnStatus:string',
      'ReturnTransactionNo:string',
    ])
  )
  """
  s = ' \
    SELECT FROM CashAdvanceTransactItem \
    [ \
      LCashAdvanceAccount.EmployeeIdNumber = :EmployeeId and\
      LTransaction.ActualDate >= :BeginDate and \
      LTransaction.ActualDate < :EndDate \
    ] \
    ( \
      TransactionItemId, \
      LTransaction.TransactionDate , \
      LTransaction.TransactionCode , \
      LTransaction.ActualDate , \
      MutationType , \
      Amount , \
      EkuivalenAmount , \
      LTransaction.ReferenceNo , \
      LTransaction.Description , \
      LTransaction.Inputer , \
      LTransaction.TransactionNo ,\
      LTransaction.AuthStatus ,\
      CurrencyCode , \
      Rate , \
      LCurrency.Short_Name , \
      LTransaction.CurrencyCode as TransCurrencyCode , \
      LTransaction.Rate as TransRate , \
      LTransaction.LCurrency.Short_Name as TransCurrencyName , \
      Self \
    ) \
    THEN ORDER BY ASC ActualDate, ASC TransactionItemId;'
  oql = config.OQLEngine.CreateOQL(s)
  oql.SetParameterValueByName('EmployeeId', EmployeeId)
  oql.SetParameterValueByName('BeginDate', BeginDate)
  oql.SetParameterValueByName('EndDate', EndDate + 1)
  oql.ApplyParamValues()

  oql.active = 1
  ds  = oql.rawresult

  """
  
  strSQL = "SELECT A.TRANSACTIONITEMID, C.TRANSACTIONDATE, C.TRANSACTIONCODE, C.ACTUALDATE, B.MUTATIONTYPE, \
    B.AMOUNT, B.EKUIVALENAMOUNT, C.REFERENCENO, C.DESCRIPTION, C.INPUTER, C.TRANSACTIONNO, \
    C.AUTHSTATUS, B.CURRENCYCODE, B.RATE, E.SHORT_NAME, C.CURRENCYCODE, C.RATE, D.SHORT_NAME, \
    G.ACCOUNTNAME, A.TRANSACTIONITEMID,  a.returntransactionitemid, \
      (select transactionno from \
         transaction.transaction tr, transaction.transactionitem ti \
         where tr.transactionid=ti.transactionid and ti.transactionitemid=a.returntransactionitemid) \
       as return_transactionno \
    FROM \
    transaction.ACCOUNTTRANSACTIONITEM A, \
    transaction.TRANSACTIONITEM B, \
    transaction.TRANSACTION C, \
    transaction.CURRENCY D, \
    transaction.CURRENCY E, \
    transaction.ACCOUNTRECEIVABLE F, \
    transaction.FINANCIALACCOUNT G \
    WHERE A.ACCOUNTTITYPE = 'C' AND \
    A.TransactionItemId = B.TransactionItemId AND \
    B.TRANSACTIONID = C.TRANSACTIONID AND \
    C.CURRENCYCODE = D.CURRENCY_CODE AND \
    B.CURRENCYCODE = E.CURRENCY_CODE AND \
    A.ACCOUNTNO = F.ACCOUNTNO AND \
    F.AccountNo = G.AccountNo AND \
    ( C.ACTUALDATE BETWEEN '%(BEGINDATE)s' AND '%(ENDDATE)s' AND F.EmployeeIdNumber = %(EmployeeId)d ) \
    ORDER BY C.ACTUALDATE ASC, A.TRANSACTIONITEMID ASC \
    " % { 'EmployeeId' : EmployeeId ,
          'BEGINDATE' : sqlBeginDateParam,
          'ENDDATE' : sqlEndDateParam
    }

  ds = config.CreateSQL(strSQL).RawResult

  # dict untuk status otorisasi
  stAuth = {'T':'Sudah Otorisasi','F':'Belum Otorisasi'}

  # dict untuk status pengembalian LPJ
  stReturn = {0 : 'Belum ada LPJ', 1 : 'Sudah Ada LPJ' }

  while not ds.Eof:
    recHist = dsHist.AddRecord()
    recHist.TransactionItemId = ds.TransactionItemId
    recHist.TransactionDate = AsDateTime(ds.ActualDate)
    recHist.TransactionDateStr = config.FormatDateTime('dd-mmm-yyyy',recHist.TransactionDate)
    recHist.TransactionCode = ds.TransactionCode
    recHist.MutationType = ds.MutationType

    TranCurrencyCode = ds.CurrencyCode_1
    TranCurrencyName = ds.Short_Name_1
    TransRate        = ds.Rate_1

    if ds.CurrencyCode != TranCurrencyCode and ds.CurrencyCode == '000':
      CurrencyCode = TranCurrencyCode
      CurrencyName = TranCurrencyName
      Rate = TransRate
      Amount      = ds.Amount / Rate
    else :
      CurrencyCode = ds.CurrencyCode
      CurrencyName = ds.Short_Name
      Rate = ds.Rate
      Amount = ds.Amount
    # end if
    
    recHist.Amount = Amount
    recHist.AmountEkuivalen = ds.EkuivalenAmount
    recHist.Rate = Rate
    recHist.CurrencyName = TranCurrencyName
    
    if ds.MutationType == 'D' :
      recHist.Debet = ds.EkuivalenAmount
      recSaldo.TotalBalance += ds.EkuivalenAmount
      recSaldo.TotalDebet += ds.EkuivalenAmount
    else:
      recHist.Kredit = ds.EkuivalenAmount
      recSaldo.TotalBalance -= ds.EkuivalenAmount
      recSaldo.TotalCredit += ds.EkuivalenAmount
    # endif
    
    recHist.ReferenceNo = ds.ReferenceNo
    recHist.Description = ds.Description
    recHist.Inputer = ds.Inputer
    recHist.TransactionNo = ds.TransactionNo
    recHist.AuthStatus = stAuth[ds.AuthStatus]
    recHist.ReturnStatus = stReturn[ds.ReturnTransactionItemid not in [0,None,'']]
    recHist.ReturnTransactionNo = ds.return_transactionno

    ds.Next()
  #-- while

