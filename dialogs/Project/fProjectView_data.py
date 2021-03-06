import com.ihsan.foundation.pobjecthelper as phelper
import simplejson

def FormSetDataEx(uideflist, params) :
  config = uideflist.config
  helper = phelper.PObjectHelper(config)
  
  oKey = params.FirstRecord.key
  uideflist.SetData('uipProject',oKey)
  
  recProject = uideflist.uipProject.Dataset.GetRecord(0)
  
  # Set Branch Name
  oBranch = helper.GetObject('Branch',recProject.BranchCode)
  recProject.BranchName = oBranch.BranchName
  
  # Set Currency Name
  oCurrency = config.CreatePObjImplProxy('Currency')
  oCurrency.key = recProject.CurrencyCode
  recProject.CurrencyName = oCurrency.Full_Name

  # Set Init Value
  Now = config.Now()
  recProject.BeginDate = Now
  recProject.EndDate = Now
  recProject.BeginningBalance = 0.0
  
def GetHistTransaction(config, params, returns):
  def AsDateTime(tdate):
    utils = config.ModLibUtils
    return utils.EncodeDate(tdate[0], tdate[1], tdate[2])

  recStatus = returns.CreateValues(
          ['BeginningBalance', 0.0],
          ['PeriodStr',''],
          ['TotalDebet',0.0],
          ['TotalCredit',0.0],
        )

  helper = phelper.PObjectHelper(config)

  rec = params.FirstRecord
  AccountNo = rec.AccountNo
  BeginDate = rec.BeginDate
  EndDate   = rec.EndDate
  
  # -- Get BeginningBalance
  oProjectAccount = helper.GetObject('ProjectAccount',AccountNo)
  recStatus.BeginningBalance = oProjectAccount.GetBalanceByDate(int(BeginDate))

  # -- Set Period
  PeriodStr = ''
  if BeginDate == EndDate :
    PeriodStr = config.FormatDateTime('dd-mm-yyyy',BeginDate)
  else:
    PeriodStr = "%s s/d %s" % (
                   config.FormatDateTime('dd-mm-yyyy',BeginDate),
                   config.FormatDateTime('dd-mm-yyyy',EndDate)
                 )
  
  recStatus.PeriodStr = PeriodStr

  # Preparing returns

  dsHist = returns.AddNewDatasetEx(
    'histori',
    ';'.join([
      'TransactionItemId: integer',
      'TransactionDate: datetime',
      'TransactionDateStr: string',
      'TransactionCode: string',
      'MutationType: string',
      'Amount: float',
      'ReferenceNo: string',
      'Description: string',
      'Inputer: string',
      'TransactionNo:string'
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
      LTransaction.ActualDate, \
      LTransaction.TransactionCode, \
      MutationType, \
      Amount, \
      LTransaction.ReferenceNo, \
      LTransaction.Description, \
      LTransaction.Inputer, \
      LTransaction.TransactionNo,\
      Self \
    ) \
    THEN ORDER BY ASC ActualDate, ASC TransactionItemId;'

  oql = config.OQLEngine.CreateOQL(s)
  oql.SetParameterValueByName('AccountNo', AccountNo)
  oql.SetParameterValueByName('BeginDate', int(BeginDate))
  oql.SetParameterValueByName('EndDate', int(EndDate) + 1)
  oql.ApplyParamValues()

  oql.active = 1
  ds  = oql.rawresult

  TotalDebet = 0.0
  TotalCredit = 0.0
  while not ds.Eof:
    recHist = dsHist.AddRecord()
    recHist.TransactionItemId = ds.TransactionItemId
    recHist.TransactionDate = AsDateTime(ds.ActualDate)
    recHist.TransactionDateStr = config.FormatDateTime('dd-mmm-yyyy',recHist.TransactionDate)
    recHist.TransactionCode = ds.TransactionCode
    recHist.MutationType = ds.MutationType
    recHist.Amount = ds.Amount
    if ds.MutationType == 'D' :
      TotalDebet += ds.Amount
    else:
      TotalCredit += ds.Amount

    recHist.ReferenceNo = ds.ReferenceNo
    recHist.Description = ds.Description
    recHist.Inputer = ds.Inputer
    recHist.TransactionNo = ds.TransactionNo

    ds.Next()
  #-- while
  recStatus.TotalDebet = TotalDebet
  recStatus.TotalCredit = TotalCredit
  
def GetProductData(config, params, returns):
  status = returns.CreateValues(
    ['Is_Err',0],['Err_Message',''],
    ['Balance',0.0], ['BranchName',''],
    ['CurrencyName',''], ['AccountNo','']
  )
  helper = phelper.PObjectHelper(config)

  rec = params.FirstRecord
  ProductId = rec.ProductId
  CurrencyCode = rec.CurrencyCode
  BranchCode = str(config.SecurityContext.GetUserInfo()[4])

  try:

    # Get Data ProductAccount
    Product = helper.GetObjectByNames('ProductAccount',
       {'ProductId' : ProductId,
        'CurrencyCode' : CurrencyCode,
        'BranchCode' : BranchCode,
        }
    )

    status.Balance = Product.Balance
    status.AccountNo = Product.AccountNo

    # Get Data Branch
    corporate = helper.CreateObject('Corporate')
    CabangInfo = corporate.GetCabangInfo(Product.BranchCode)

    status.BranchName = CabangInfo.Nama_Cabang

    # Get Data Currency
    app = config.AppObject
    res = app.rexecscript(
                 'accounting',
                 'appinterface/Currency.GetCurrencyInfo',
                 app.CreateValues(['Kode_Valuta',Product.CurrencyCode])
          )
    status.CurrencyName = res.FirstRecord.short_name
  except:
    status.Is_Err = 1
    status.Err_Message = str(sys.exc_info()[1])

