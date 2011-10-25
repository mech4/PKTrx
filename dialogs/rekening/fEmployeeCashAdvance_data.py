import com.ihsan.foundation.pobjecthelper as phelper
import simplejson

def FormSetDataEx(uideflist, params) :
  config = uideflist.config

  rec = uideflist.uipEmployeeAR.Dataset.AddRecord()
  rec.BranchCode = str(config.SecurityContext.GetUserInfo()[4])

  Now = config.Now()
  
  y = config.ModLibUtils.DecodeDate(Now)[0]
  rec.BeginDate = config.ModLibUtils.EncodeDate(y,1,1)
  rec.EndDate = int(Now)

def GetHistTransaction(config, params, returns):
  def AsDateTime(tdate):
    utils = config.ModLibUtils
    return utils.EncodeDate(tdate[0], tdate[1], tdate[2])

  helper = phelper.PObjectHelper(config)

  rec = params.FirstRecord
  AccountNo = rec.AccountNo
  BeginDate = int(rec.BeginDate)
  EndDate   = int(rec.EndDate)

  # Preparing returns
  AccountReceivable = helper.GetObject('EmployeeAccountReceivable',AccountNo)
  
  BeginningBalance = AccountReceivable.GetBalanceByDate(BeginDate)

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
      'Debet: float',
      'Kredit: float',
      'ReferenceNo: string',
      'Description: string',
      'Inputer: string',
      'TransactionNo:string',
      'Total:float',
      'AuthStatus:string',
    ])
  )

  s = ' \
    SELECT FROM AccountTransactionItem \
    [ \
      AccountNo = :AccountNo and \
      LTransaction.ActualDate >= :BeginDate and \
      LTransaction.ActualDate < :EndDate \
    ] \
    ( \
      TransactionItemId, \
      LTransaction.TransactionDate, \
      LTransaction.TransactionCode, \
      LTransaction.ActualDate, \
      MutationType, \
      Amount, \
      LTransaction.ReferenceNo, \
      LTransaction.Description, \
      LTransaction.Inputer, \
      LTransaction.TransactionNo,\
      LTransaction.AuthStatus,\
      Self \
    ) \
    THEN ORDER BY ASC ActualDate, ASC TransactionItemId;'

  oql = config.OQLEngine.CreateOQL(s)
  oql.SetParameterValueByName('AccountNo', AccountNo)
  oql.SetParameterValueByName('BeginDate', BeginDate)
  oql.SetParameterValueByName('EndDate', EndDate + 1)
  oql.ApplyParamValues()

  oql.active = 1
  ds  = oql.rawresult

  stAuth = {'T':'Sudah Otorisasi','F':'Belum Otorisasi'}
  while not ds.Eof:
    recHist = dsHist.AddRecord()
    recHist.TransactionItemId = ds.TransactionItemId
    recHist.TransactionDate = AsDateTime(ds.ActualDate)
    recHist.TransactionDateStr = config.FormatDateTime('dd-mmm-yyyy',recHist.TransactionDate)
    recHist.TransactionCode = ds.TransactionCode
    recHist.MutationType = ds.MutationType
    recHist.Amount = ds.Amount
    if ds.MutationType == 'D' :
      recHist.Debet = ds.Amount
      recSaldo.TotalBalance += ds.Amount
      recSaldo.TotalDebet += ds.Amount
    else:
      recHist.Kredit = ds.Amount
      recSaldo.TotalBalance -= ds.Amount
      recSaldo.TotalCredit += ds.Amount
    # endif
    recHist.ReferenceNo = ds.ReferenceNo
    recHist.Description = ds.Description
    recHist.Inputer = ds.Inputer
    recHist.TransactionNo = ds.TransactionNo
    recHist.AuthStatus = stAuth[ds.AuthStatus]

    ds.Next()
  #-- while

