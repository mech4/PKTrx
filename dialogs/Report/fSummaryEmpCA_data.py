import com.ihsan.foundation.pobjecthelper as phelper
import sys

def FormSetDataEx(uideflist, parameter) :
  config = uideflist.Config
  rec = uideflist.uipData.Dataset.AddRecord()
  rec.BranchCode = str(config.SecurityContext.GetUserInfo()[4])
  rec.BranchName = str(config.SecurityContext.GetUserInfo()[5])

  Now = config.Now()

  y = config.ModLibUtils.DecodeDate(Now)[0]
  rec.BeginDate = config.ModLibUtils.EncodeDate(y,1,1)
  rec.EndDate = int(Now)


def AsDateTime(config,tdate):
  utils = config.ModLibUtils
  return utils.EncodeDate(tdate[0], tdate[1], tdate[2])


def SummaryEmpCA(config,params,returns):
  status = returns.CreateValues(
     ['Is_Err',0],['Err_Message',''],
     ['PeriodStr',''],['BranchName',''],
     ['BeginDateStr',''],['EndDateStr',''],
     ['BeginBalance',0.0],
     ['TotalDebet',0.0],
     ['TotalCredit',0.0],
     ['EndBalance',0.0],
     ['TotalDebetHist',0.0],
     ['TotalCreditHist',0.0],
  )
  
  BranchCode = params.FirstRecord.BranchCode
  BeginDate = params.FirstRecord.BeginDate
  EndDate = params.FirstRecord.EndDate
  
  try:
    helper = phelper.PObjectHelper(config)
    
    corporate = helper.CreateObject('Corporate')
    CabangInfo = corporate.GetCabangInfo(BranchCode)

    status.BranchName = CabangInfo.Nama_Cabang
    status.BeginDateStr = config.FormatDateTime('dd-mm-yyyy',BeginDate)
    status.EndDateStr = config.FormatDateTime('dd-mm-yyyy',EndDate)
    if BeginDate == EndDate :
      status.PeriodStr = config.FormatDateTime('dd-mm-yyyy',BeginDate)
    else:
      status.PeriodStr = "%s s/d %s" % (
                   config.FormatDateTime('dd-mm-yyyy',BeginDate),
                   config.FormatDateTime('dd-mm-yyyy',EndDate)
                 )
    # end if
    
    # Set DATE SQL PARAM
    sqlBeginDateParam = config.FormatDateTime('yyyy-mm-dd',BeginDate)
    sqlEndDateParam = config.FormatDateTime('yyyy-mm-dd',EndDate + 1)
    
    dsSummary = returns.AddNewDatasetEx(
     'summary',
     ';'.join([
       'NomorKaryawan: string',
       'NamaKaryawan: string',
       'Debet: float',
       'Kredit: float',
       'TotalMutasi: float',
       'SaldoAwal: float',
       'SaldoAkhir: float',
       'CurrencyName: string'
     ])
    )

    
    strSQL = " \
              select b.employeeidnumber, a.accountno, a.accountname, a.currencycode, c.short_name, \
              ( select sum(case when d.mutationtype='D' then d.Amount \
                           else -d.Amount \
                      end) \
              from transactionitem d, transaction e, accounttransactionitem f\
              where d.transactionid=e.transactionid \
                 and d.transactionitemid=f.transactionitemid \
                 and f.accountno = a.accountno and e.actualdate < '%(BEGINDATE)s' ) as BeginBalance, \
                 (select sum(d.Amount) \
                     from transaction.transaction c, \
                          transaction.transactionitem d, \
                          transaction.accounttransactionitem e \
                     where c.transactionid = d.transactionid and d.transactionitemid = e.transactionitemid \
                         and c.actualdate between '%(BEGINDATE)s' and '%(ENDDATE)s'  and e.accountno=a.accountno \
                         and d.mutationtype='D') as Debet, \
                 (select sum(d.Amount) \
                     from transaction.transaction c, \
                          transaction.transactionitem d, \
                          transaction.accounttransactionitem e \
                     where c.transactionid = d.transactionid and d.transactionitemid = e.transactionitemid \
                         and c.actualdate between '%(BEGINDATE)s' and '%(ENDDATE)s'  and e.accountno=a.accountno \
                         and d.mutationtype='C') as Kredit \
              from transaction.financialaccount a, transaction.accountreceivable b, transaction.currency c \
              where a.accountno = b.accountno \
                  and a.currencycode = c.currency_code \
                  and b.AccountReceivableType = 'C' \
                  and a.branchcode = '%(BRANCHCODE)s' \
                 order by  a.accountname \
                " % {
                  'BRANCHCODE' : BranchCode ,
                  'BEGINDATE' : sqlBeginDateParam,
                  'ENDDATE' : sqlEndDateParam
               }

    res = config.CreateSQL(strSQL).RawResult

    while not res.Eof:
      recSum = dsSummary.AddRecord()
      #recSum.NomorKaryawan = res.AccountNo
      recSum.NomorKaryawan = str(res.EmployeeIdNumber)
      recSum.NamaKaryawan = res.AccountName
      recSum.CurrencyName = res.Short_Name
      recSum.Debet = res.Debet or 0.0
      recSum.Kredit = res.Kredit or 0.0
      recSum.TotalMutasi = (res.Debet or 0.0 ) - ( res.Kredit or 0.0)
      
      #AccountR = helper.GetObject('AccountReceivable',res.AccountNo)
      SaldoAwal = res.BeginBalance or 0.0 #AccountR.GetBalanceByDate(BeginDate)

      recSum.SaldoAwal = SaldoAwal
      recSum.SaldoAkhir = SaldoAwal + recSum.TotalMutasi
      
      status.BeginBalance += recSum.SaldoAwal
      status.TotalDebet += recSum.Debet
      status.TotalCredit += recSum.Kredit
      status.EndBalance += recSum.SaldoAkhir
      
      res.Next()
      
    # end while
    
    
    #--- GET HISTORI TRANSAKSI
    dsHist = returns.AddNewDatasetEx(
      'historitransaksi',
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
        'AccountName:string',
        'ReturnStatus:string',
        'ReturnTransactionNo:string',
      ])
    )

    """
    s = ' \
      SELECT FROM CashAdvanceTransactItem \
      [ \
        LTransaction.ActualDate >= :BeginDate and \
        LTransaction.ActualDate < :EndDate and \
        BranchCode = :BranchCode \
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
        LCashAdvanceAccount.AccountName, \
        Self \
      ) \
      THEN ORDER BY ASC ActualDate, ASC TransactionItemId;'

    oql = config.OQLEngine.CreateOQL(s)
    oql.SetParameterValueByName('BeginDate', BeginDate)
    oql.SetParameterValueByName('EndDate', EndDate + 1)
    oql.SetParameterValueByName('BranchCode', BranchCode)
    oql.ApplyParamValues()

    oql.active = 1
    ds  = oql.rawresult """
    
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
        ( C.ACTUALDATE BETWEEN '%(BEGINDATE)s' AND '%(ENDDATE)s' AND B.BRANCHCODE = '%(BRANCHCODE)s' ) \
        ORDER BY C.ACTUALDATE ASC, A.TRANSACTIONITEMID ASC \
        " % { 'BRANCHCODE' : BranchCode ,
              'BEGINDATE' : sqlBeginDateParam,
              'ENDDATE' : sqlEndDateParam
        }

    ds = config.CreateSQL(strSQL).RawResult

    ds.First()

    # dict untuk status otorisasi
    stAuth = {'T':'Sudah Otorisasi','F':'Belum Otorisasi'}

    # dict untuk status pengembalian LPJ
    stReturn = {0 : 'Belum ada LPJ', 1 : 'Sudah Ada LPJ' }
    
    while not ds.Eof:
      recHist = dsHist.AddRecord()
      recHist.TransactionItemId = ds.TransactionItemId
      recHist.TransactionDate = AsDateTime(config, ds.ActualDate)
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
        #recSaldo.TotalBalance += ds.EkuivalenAmount
        status.TotalDebetHist += ds.EkuivalenAmount
      else:
        recHist.Kredit = ds.EkuivalenAmount
        #recSaldo.TotalBalance -= ds.EkuivalenAmount
        status.TotalCreditHist += ds.EkuivalenAmount
      # endif

      recHist.ReferenceNo = ds.ReferenceNo
      recHist.Description = ds.Description
      recHist.Inputer = ds.Inputer
      recHist.TransactionNo = ds.TransactionNo
      recHist.AccountName = ds.AccountName
      recHist.AuthStatus = stAuth[ds.AuthStatus]
      recHist.ReturnStatus = stReturn[ds.ReturnTransactionItemid not in [0,None,'']]
      recHist.ReturnTransactionNo = ds.return_transactionno

      ds.Next()
    #-- while
    
  except:
    status.Is_Err = 1
    status.Err_Message = str(sys.exc_info()[1])
