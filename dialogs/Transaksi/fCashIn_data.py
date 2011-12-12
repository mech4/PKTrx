import com.ihsan.foundation.pobjecthelper as phelper
import sys
import simplejson

def FormSetDataEx(uideflist, params) :
  config = uideflist.config
  helper = phelper.PObjectHelper(uideflist.config)

  if params.GetDatasetByName('trparam') != None :
    oForm = helper.CreateObject('FormTransaksi')
    oForm.SetDataEx(uideflist,params)

    uipTran = uideflist.uipTransaction.Dataset.GetRecord(0)
    oTran = helper.GetObjectByNames('Transaction',{'TransactionNo' : uipTran.TransactionNo})

    if uipTran.PaymentType == 'B' :
      uipTran.RateBank = oTran.Rate
    elif uipTran.PaymentType == 'C':
      uipTran.RateCash = oTran.Rate
      uipTran.SetFieldByName('LCurrencyCash.Currency_Code', oTran.CurrencyCode)
      uipTran.SetFieldByName('LCurrencyCash.Short_Name', oTran.LCurrency.Short_Name)
    # end if
    
    TotalItem = uideflist.uipTransactionItem.Dataset.RecordCount
    uipItem = uideflist.uipTransactionItem.Dataset
    for i in range(TotalItem):
      recItem = uipItem.GetRecord(i)

      AccountCode = recItem.AccountCode

      oAccount = helper.GetObject('Account',AccountCode)
      if oAccount.isnull :
        oMapAccount = helper.GetObject('MapAccount',AccountCode)
        if not oMapAccount.isnull :
          recItem.AccountCode = oMapAccount.NewAccount
        # end if
      # end if
    # end for

    return

  Now = int(config.Now())
  recT = uideflist.uipTransaction.Dataset.AddRecord()
  recT.Inputer = str(config.SecurityContext.UserId)
  recT.PaidTo = recT.Inputer
  recT.BranchCode = str(config.SecurityContext.GetUserInfo()[4])
  recT.TransactionDate = Now
  recT.ActualDate = Now
  recT.FloatTransactionDate = Now
  recT.Rate = 1.0
  recT.TotalAmount = 0.0
  recT.CashType = 'C'

  # Set Transaction Number
  recT.TransactionNo = '<AUTOGENERATED>' #GenerateTransactionNumber(config,helper)

  aUserInfo = config.SecurityContext.GetUserInfo()
  aBranchCode = str(aUserInfo[4])
  aBranchName = str(aUserInfo[5])

  recT.SetFieldByName('LValuta.Currency_Code', '000')
  recT.SetFieldByName('LValuta.Full_Name', 'Indonesia Rupiah')
  recT.SetFieldByName('LValuta.Kurs_Tengah_BI', 1.0)

  Now = config.Now()
  bulan = int(config.FormatDateTime('m',Now))
  tahun = int(config.FormatDateTime('yyyy',Now))
  rsPeriod = config.CreateSQL(' \
     select a.periodid from budgetperiod a , budgetperiod b \
     where a.parentperiodid=b.periodid \
         and a.periodvalue=%d and b.periodvalue=%d' % (bulan,tahun)).RawResult

  recT.PeriodId =  rsPeriod.GetFieldValueAt(0) or 0

def GenerateTransactionNumber(config,helper):
  oService = helper.LoadScript('Transaction.TransactionHelper')
  return oService.GetTransactionNumber(config,'CI')

def SimpanData(config, params, returns):
  IsErr = 0
  ErrMessage = ''
  StreamName = ''
  TransactionId = 0
  IsCetakBSZ = 0
  NewTransactionNo = ''
  TransactionNo = ''

  helper = phelper.PObjectHelper(config)
  try :
    oTransaction = params.uipTransaction.GetRecord(0)

    request = {}
    request['ReferenceNo'] = oTransaction.ReferenceNo
    request['Description'] = oTransaction.Description
    request['ActualDate'] = oTransaction.ActualDate
    request['Amount'] = oTransaction.TotalAmount
    request['Rate'] = oTransaction.Rate
    request['CurrencyCode'] = oTransaction.CurrencyCode
    request['RateCash'] = oTransaction.RateCash
    request['RateBank'] = oTransaction.RateBank

    request['Inputer'] = oTransaction.Inputer
    request['TransactionNo'] = oTransaction.TransactionNo
    request['PaidTo'] = oTransaction.PaidTo
    request['ReceivedFrom'] = oTransaction.ReceivedFrom
    request['BankAccountNo'] = oTransaction.GetFieldByName('LBank.AccountNo')
    request['AssetCode'] = oTransaction.GetFieldByName('LAsset.Account_Code')
    request['AssetName'] = oTransaction.GetFieldByName('LAsset.Account_Name')
    request['AssetCurrency'] = oTransaction.GetFieldByName('LValuta.Currency_Code')
    request['BranchCode'] = config.SecurityContext.GetUserInfo()[4]
    request['PaymentType'] = oTransaction.PaymentType

    items = []

    for i in range(params.uipTransactionItem.RecordCount):
      oItem = params.uipTransactionItem.GetRecord(i)
      item = {}
      item['AccountCode'] = oItem.AccountCode
      item['AccountName'] = oItem.AccountName
      item['Amount'] = oItem.Amount
      item['Valuta'] = oItem.GetFieldByName('LCurrency.Currency_Code')
      item['Rate']   = oItem.Rate
      item['Ekuivalen'] = oItem.Ekuivalen
      item['Description'] = oItem.Description
      item['BudgetId'] = oItem.BudgetId

      items.append(item)
    #-- for

    request['Items']= items
    sRequest = simplejson.dumps(request)

    oService = helper.LoadScript('Transaction.CashIn')

    if oTransaction.ShowMode == 1 :
      response = oService.CashInNew(config, sRequest,params)
    else :
      response = oService.CashInUpdate(config, sRequest,params)

    response = simplejson.loads(response)

    TransactionNo = response[u'TransactionNo']
    filename = response[u'FileKwitansi']
    
    sw = returns.AddStreamWrapper()
    sw.Name = 'Kwitansi'
    sw.LoadFromFile(filename)
    #sw.MIMEType = config.AppObject.GetMIMETypeFromExtension(filename)
    sw.MIMEType = 'application/msword'

    StreamName = sw.Name
    
    #if oTransaction.SaveMode == 1 :
    #  NewTransactionNo = GenerateTransactionNumber(config,helper)
    IsErr = response[u'Status']
    ErrMessage = response[u'ErrMessage']

  except :
    IsErr = 1
    ErrMessage = str(sys.exc_info()[1])

  returns.CreateValues(
      ['IsErr', IsErr],
      ['ErrMessage', ErrMessage],
      ['StreamName',StreamName],
      ['TransactionId',TransactionId],
      ['IsCetakBSZ',IsCetakBSZ],
      ['NewTransactionNo',NewTransactionNo],
      ['TransactionNo',TransactionNo],
  )

